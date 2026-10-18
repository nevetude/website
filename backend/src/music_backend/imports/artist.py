from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from music_backend.enums import ArtistType, ImportKind, ImportState
from music_backend.imports.common import (
    Context,
    Follow,
    Task,
    add_if_missing,
    description_of,
    get_or_create_artist_stub,
    log_changes,
    upsert,
)
from music_backend.models import Artist, ArtistAlias, ArtistMember

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession


def _related(raw: Mapping[str, Any], relationship_type: str) -> list[dict[str, Any]]:
    """Artists on one side of `artist_relationships`: "members" (of a group) or "member_of" (groups)."""
    return next(
        (
            relation["artists"]
            for relation in raw["artist_relationships"]
            if relation["relationship_type"] == relationship_type
        ),
        [],
    )


async def handle_artist(ctx: Context, session: AsyncSession, task: Task) -> list[Task]:
    """The artist, its aliases and its group links. `follow` says which links to walk (see `Follow`):

    - the members of a walked artist are imported in full, and so are the groups they belong to, with
      the members of those groups; nothing beyond that (other groups of those members stay stubs);
    - the groups of a walked artist are imported in full with their members, and no further.
    """
    raw = (await ctx.get(f"/artists/{task.genius_id}"))["artist"]
    members, groups = _related(raw, "members"), _related(raw, "member_of")
    components = raw["name_components"]  # Genius splits artist names itself

    artist, changes = await upsert(
        session,
        Artist,
        task.genius_id,
        {
            "name": raw["name"],
            "base_name": components["base_name"],
            "disambiguator": components["disambiguator"],
            # Genius gives no artist type: members mean a group, everyone else is a person by default.
            "artist_type": ArtistType.GROUP if members else ArtistType.PERSON,
            "description": description_of(raw["description"]["dom"]),
            "genius_url": raw["url"],
            "cover_url": raw["image_url"],
            "is_verified": raw["is_verified"],
            "is_meme_verified": raw["is_meme_verified"],
            "followers_count": raw["followers_count"],
            "import_state": ImportState.FULL,
        },
    )

    for position, member in enumerate(members, start=1):
        stub = await get_or_create_artist_stub(session, member)
        await add_if_missing(
            session, ArtistMember, {"group_id": artist.id, "member_id": stub.id}, position=position
        )
    for group in groups:
        stub = await get_or_create_artist_stub(session, group, ArtistType.GROUP)
        await add_if_missing(session, ArtistMember, {"group_id": stub.id, "member_id": artist.id})
    if added := await _add_aliases(session, artist.id, raw["alternate_names"]):
        changes["aliases_added"] = [[], added]

    await log_changes(session, "artist", artist, raw, changes)
    queued: list[Task] = []
    if Follow.MEMBERS in task.follow:
        # Members found from the top artist look for their other groups; members of a group found that way do not.
        follow = Follow.GROUPS if Follow.GROUPS in task.follow else Follow.NONE
        queued += [Task(ImportKind.ARTIST, a["id"], follow, name=a["name"]) for a in members]
    if Follow.GROUPS in task.follow:
        queued += [Task(ImportKind.ARTIST, a["id"], Follow.MEMBERS, name=a["name"]) for a in groups]
    return queued


async def handle_discography(ctx: Context, session: AsyncSession, task: Task) -> list[Task]:
    """The artist first (with the walk over its members and groups), then the list of its newest albums
    (all, or `limit`). The tasks it returns are the units of the job: what the artist walk found, then
    each album. The list itself writes nothing."""
    artist = Task(ImportKind.ARTIST, task.genius_id)
    queued = await handle_artist(ctx.for_task(artist), session, artist)
    albums: list[dict[str, Any]] = []
    page: int | None = 1
    while page and (task.limit is None or len(albums) < task.limit):
        data = await ctx.get(
            f"/artists/{task.genius_id}/albums",
            {"per_page": 50, "page": page},
        )
        albums += data["albums"]
        page = data["next_page"]
    return [
        *queued,
        *(Task(ImportKind.ALBUM, a["id"], name=a["name"]) for a in albums[: task.limit]),
    ]


async def _add_aliases(session: AsyncSession, artist_id: int, names: list[str]) -> list[str]:
    """Add aliases that are missing; existing ones (possibly typed by hand) are never removed."""
    known = set(
        await session.scalars(select(ArtistAlias.name).where(ArtistAlias.artist_id == artist_id))
    )
    added = [name for name in dict.fromkeys(names) if name not in known]
    session.add_all(ArtistAlias(artist_id=artist_id, name=name) for name in added)
    return added
