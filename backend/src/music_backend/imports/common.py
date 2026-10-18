"""What every handler shares: the work item, the context, and the small helpers that write Genius data."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date
from enum import Flag, auto
from typing import TYPE_CHECKING, Any

from pydantic_core import to_jsonable_python
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.enums import ArtistType, DatePrecision, ImportKind, ImportState, RevisionAction
from music_backend.models import (
    Album,
    AlbumTrack,
    Artist,
    CreditRole,
    GeniusResponse,
    Revision,
    Song,
)

if TYPE_CHECKING:
    from music_backend.imports.client import GeniusClient, Recorder, RequestLog


class Follow(Flag):
    """The links of a task a handler may queue. An artist has two directions, so a flag and not a bool:
    this is how the walk over groups is cut off after exactly one step in each direction.
    RELATED is the one link of an album: the other editions of it."""

    NONE = 0
    MEMBERS = auto()
    GROUPS = auto()
    RELATED = auto()
    ALL = MEMBERS | GROUPS | RELATED


@dataclass(slots=True, frozen=True)
class Task:
    """One thing to import. `follow` lets a handler queue the links it is allowed to follow."""

    kind: ImportKind
    genius_id: int
    follow: Follow = Follow.ALL
    limit: int | None = None  # discography only: how many of the newest albums
    # Only for people to read (progress, request log): the list that named the task already knows it.
    name: str | None = field(default=None, compare=False)

    @property
    def key(self) -> tuple[ImportKind, int]:
        return self.kind, self.genius_id


@dataclass(slots=True, frozen=True)
class Context:
    client: GeniusClient
    record: Recorder | None = None

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.client.get(path, params, self.record)

    def for_task(self, task: Task) -> Context:
        """The same context whose request log also says which task each request was made for."""
        record = self.record
        if record is None:
            return self

        async def tagged(entry: RequestLog) -> None:
            # The most specific task wins: a handler may call another one for a part of its work.
            await record(
                replace(
                    entry,
                    task_kind=entry.task_kind or task.kind,
                    task_genius_id=entry.task_genius_id or task.genius_id,
                    task_name=entry.task_name or task.name,
                )
            )

        return Context(self.client, tagged)


# A handler saves one entity inside the session it is given and returns the tasks it found.
type Handler = Callable[[Context, AsyncSession, Task], Awaitable[list[Task]]]


# Block tags: their texts are separated by a blank line, as Genius does in its own `plain` format.
_BLOCKS = {"root", "p", "blockquote", "center", "hr"}


def plain_text(node: Mapping[str, Any] | str) -> str:
    """The text of a Genius `dom` tree. Genius also writes this text itself (`text_format=plain`), and
    this gives the same one for 92 of 95 sampled descriptions (the rest differ by blank lines at the end)."""
    if isinstance(node, str):
        return node
    if node["tag"] == "br":
        return "\n"
    children = node.get("children", [])  # `br`, `hr` and `img` have none
    if node["tag"] in _BLOCKS and any(
        not isinstance(c, str) and c["tag"] in _BLOCKS for c in children
    ):
        parts = [plain_text(c) for c in children if not isinstance(c, str) or c.strip()]
        return "\n\n".join(part for part in parts if part)
    return "".join(plain_text(c) for c in children)


def description_of(dom: Mapping[str, Any]) -> str | None:
    """The searchable text of a description. Genius writes "?" (or nothing) where there is none."""
    text = plain_text(dom).strip()
    return None if text in ("", "?") else text


def partial_date(
    components: Mapping[str, int | None] | None,
) -> tuple[date | None, DatePrecision | None]:
    """Genius pads unknown parts with 1 in `release_date`; the components say what is really known.

    A song with no date at all has no components either (`null`, not a dict of nulls).
    """
    if components is None or components["year"] is None:
        return None, None
    year, month, day = components["year"], components["month"], components["day"]
    precision = DatePrecision.DAY if day else DatePrecision.MONTH if month else DatePrecision.YEAR
    return date(year, month or 1, day or 1), precision


def apply_fields(entity: Any, values: Mapping[str, Any]) -> dict[str, list[Any]]:
    """Set the fields; return {field: [old, new]} for what changed."""
    changes: dict[str, list[Any]] = {}
    for name, new in values.items():
        old = getattr(entity, name)
        if old != new:
            changes[name] = [old, new]
            setattr(entity, name, new)
    return changes


async def upsert(
    session: AsyncSession, model: Any, genius_id: int, values: Mapping[str, Any]
) -> tuple[Any, dict[str, list[Any]]]:
    """Create or update the entity with this Genius id; a stub becomes a full entity this way."""
    entity = await session.scalar(select(model).where(model.genius_id == genius_id))
    if entity is None:
        entity = model(genius_id=genius_id, **values)
        session.add(entity)
        changes: dict[str, list[Any]] = {"genius_id": [None, genius_id]}
    else:
        changes = apply_fields(entity, values)
    await session.flush()
    return entity, changes


async def log_changes(
    session: AsyncSession, entity_type: str, entity: Any, raw: Any, changes: dict[str, list[Any]]
) -> None:
    """Keep the Genius response of the entity and write the history entry of an import.

    The response is replaced whenever it differs from the stored one (Genius also changes what we do not
    store, and the response lives in its own table, so that costs the entity rows nothing); the history
    entry is only for a real change of the stored fields."""
    response = insert(GeniusResponse).values(entity_type=entity_type, entity_id=entity.id, raw=raw)
    await session.execute(
        response.on_conflict_do_update(
            index_elements=["entity_type", "entity_id"],
            set_={"raw": raw, "updated_at": func.now()},
            where=GeniusResponse.raw.is_distinct_from(response.excluded.raw),
        )
    )
    if changes:
        session.add(
            Revision(
                entity_type=entity_type,
                entity_id=entity.id,
                user_id=None,  # system
                action=RevisionAction.IMPORT,
                changes=to_jsonable_python(changes),  # dates and enums are not plain JSON
            )
        )


async def find_or_insert(
    session: AsyncSession, model: Any, lookup: Mapping[str, Any], **values: Any
) -> Any:
    """Handlers run in parallel and meet the same new row (an artist in two songs, the role "Writer").
    ON CONFLICT makes the second one wait for the first and then read its row, instead of failing."""
    query = select(model).filter_by(**lookup)
    row = await session.scalar(query)
    if row is None:
        await session.execute(insert(model).values(**lookup, **values).on_conflict_do_nothing())
        row = await session.scalar(query)
    return row


async def get_or_create_stub(
    session: AsyncSession, model: Any, genius_id: int, **values: Any
) -> Any:
    """An entity known only from a list: id and name, no request of its own."""
    return await find_or_insert(
        session, model, {"genius_id": genius_id}, import_state=ImportState.STUB, **values
    )


async def get_or_create_artist_stub(
    session: AsyncSession, raw: Mapping[str, Any], artist_type: ArtistType | None = None
) -> Artist:
    # Genius sends no name parts for list entries; they are fixed when the artist is imported in full.
    artist: Artist = await get_or_create_stub(
        session,
        Artist,
        raw["id"],
        name=raw["name"],
        base_name=raw["name"],
        cover_url=raw["image_url"],
        artist_type=artist_type,  # only known when somebody lists the stub as a group
    )
    # A stub is only known to be a group once somebody lists it as one.
    if artist_type is ArtistType.GROUP and artist.import_state is ImportState.STUB:
        artist.artist_type = ArtistType.GROUP
    return artist


async def get_or_create_album_stub(session: AsyncSession, raw: Mapping[str, Any]) -> Album:
    stub: Album = await get_or_create_stub(
        session,
        Album,
        raw["id"],
        name=raw["name"],
        base_name=raw["name"],  # split when the album is imported in full
        cover_url=raw["cover_art_url"],
    )
    return stub


async def get_or_create_song_stub(session: AsyncSession, raw: Mapping[str, Any]) -> Song:
    stub: Song = await get_or_create_stub(
        session, Song, raw["id"], name=raw["title"], base_name=raw["title"]
    )
    return stub


async def add_if_missing(
    session: AsyncSession, model: Any, keys: Mapping[str, Any], **extra: Any
) -> None:
    """Add a link row unless one with these keys exists."""
    conditions = [getattr(model, name) == value for name, value in keys.items()]
    if await session.scalar(select(model).where(*conditions).limit(1)) is None:
        session.add(model(**keys, **extra))


async def add_credits(
    session: AsyncSession,
    model: Any,
    owner: Mapping[str, int],
    groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The credit rows of an album or a song (`owner` is `{"song_id": 5}`): one role per Genius group.
    Returns the artists found, which the caller queues for import."""
    artists: list[dict[str, Any]] = []
    for group in groups:
        role = await find_or_insert(session, CreditRole, {"name": group["label"]})
        for artist in group["artists"]:
            stub = await get_or_create_artist_stub(session, artist)
            keys = {**owner, "artist_id": stub.id, "role_id": role.id}
            await add_if_missing(session, model, keys, label_text=group["label"])
            artists.append(artist)
    return artists


async def find_placement(session: AsyncSession, album_id: int, song_id: int) -> AlbumTrack | None:
    """The song's place on an album."""
    return await session.scalar(
        select(AlbumTrack).where(AlbumTrack.album_id == album_id, AlbumTrack.song_id == song_id)
    )
