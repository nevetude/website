"""SQL pieces shared by the API modules: what a role is, the album card, ordering, counting."""

import re
from collections.abc import Iterator, Mapping
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import (
    ColumnElement,
    Select,
    Subquery,
    and_,
    case,
    func,
    literal,
    select,
    union,
)
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import literal_column
from sqlalchemy.sql.elements import SQLColumnExpression, UnaryExpression

from music_backend.api.schemas import ChangeOut, DomNode, DomRef, ImportRef
from music_backend.enums import ImportKind, SongArtistRole
from music_backend.models import (
    Album,
    AlbumArtist,
    AlbumCredit,
    AlbumTrack,
    Artist,
    Base,
    CreditRole,
    GeniusResponse,
    ImportJob,
    Revision,
    SongArtist,
    SongCredit,
)


async def get_or_404[M: Base](session: AsyncSession, model: type[M], pk: int) -> M:
    row = await session.get(model, pk)
    if row is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return row


def raw_of(entity_type: str, entity_id: int) -> ColumnElement[bool]:
    """The `where` for the Genius response of one entity (`select(GeniusResponse.raw).where(...)`)."""
    return and_(GeniusResponse.entity_type == entity_type, GeniusResponse.entity_id == entity_id)


_ENTITY_PATH = re.compile(r"^/(artists|albums)/(\d+)$")


def _api_paths(node: Mapping[str, Any] | str) -> Iterator[str]:
    if isinstance(node, str):
        return
    if node.get("data") and "api_path" in node["data"]:
        yield node["data"]["api_path"]
    for child in node.get("children") or []:
        yield from _api_paths(child)


async def _refs(
    session: AsyncSession,
    model: type[Artist] | type[Album],
    kind: Literal["artist", "album"],
    found: Mapping[str, tuple[str, int]],
) -> list[DomRef]:
    plural = f"{kind}s"
    wanted = {genius_id for name, genius_id in found.values() if name == plural}
    rows = await session.execute(
        select(model.genius_id, model.id).where(model.genius_id.in_(wanted))
    )
    return [DomRef(api_path=f"/{plural}/{genius_id}", kind=kind, id=pk) for genius_id, pk in rows]


async def description_tree(
    session: AsyncSession, entity_type: str, entity_id: int, path: tuple[str | int, ...]
) -> tuple[DomNode | None, list[DomRef]]:
    """The `dom` tree of a description, read from the stored Genius response (null for a stub, or for an
    entity imported before descriptions were kept as trees), and what its links lead to among our pages."""
    raw = await session.scalar(
        select(GeniusResponse.raw[path]).where(raw_of(entity_type, entity_id))
    )
    if raw is None:
        return None, []
    found = {
        m.group(0): (m.group(1), int(m.group(2)))
        for p in _api_paths(raw)
        if (m := _ENTITY_PATH.match(p))
    }
    refs = [
        *await _refs(session, Artist, "artist", found),
        *await _refs(session, Album, "album", found),
    ]
    return DomNode.model_validate(raw), refs


async def count(session: AsyncSession, query: Select[Any]) -> int:
    return await session.scalar(select(func.count()).select_from(query.subquery())) or 0


async def imports_and_history(
    session: AsyncSession,
    entity_type: str,
    entity_id: int,
    genius_id: int | None,
    kinds: list[ImportKind],
) -> tuple[list[ImportRef], list[ChangeOut]]:
    """The jobs that imported this entity (latest first) and the last changes made to it."""
    # A manual entity has no genius_id, and no job has a NULL one: the list is empty then.
    jobs = await session.scalars(
        select(ImportJob)
        .where(ImportJob.genius_id == genius_id, ImportJob.kind.in_(kinds))
        .order_by(ImportJob.id.desc())
        .limit(10)
    )
    revisions = await session.scalars(
        select(Revision)
        .where(Revision.entity_type == entity_type, Revision.entity_id == entity_id)
        .order_by(Revision.id.desc())
        .limit(20)
    )
    return (
        [ImportRef.model_validate(job, from_attributes=True) for job in jobs],
        [ChangeOut.model_validate(row, from_attributes=True) for row in revisions],
    )


def ordering(
    keys: Mapping[str, tuple[SQLColumnExpression[Any], str]],
    sort: str,
    order: str | None,
) -> UnaryExpression[Any]:
    """`keys` maps a sort name to its column and its first direction; unknown values go last."""
    key, first = keys[sort]
    return (key.asc() if (order or first) == "asc" else key.desc()).nulls_last()


# A work is related to an artist by a *role*: Artist or Featured (the credit line) or the label of
# a credit (Writer, Producer, ...). One work can have several roles of the same artist.


def song_roles() -> Subquery:
    """(artist_id, song_id, role)"""
    return union(
        select(
            SongArtist.artist_id,
            SongArtist.song_id,
            case(
                (SongArtist.role == SongArtistRole.PRIMARY, literal("Artist")),
                else_=literal("Featured"),
            ).label("role"),
        ),
        select(SongCredit.artist_id, SongCredit.song_id, CreditRole.name).join(
            CreditRole, CreditRole.id == SongCredit.role_id
        ),
    ).subquery("song_role")


def album_roles() -> Subquery:
    """(artist_id, album_id, role)"""
    return union(
        select(AlbumArtist.artist_id, AlbumArtist.album_id, literal("Artist").label("role")),
        select(AlbumCredit.artist_id, AlbumCredit.album_id, CreditRole.name).join(
            CreditRole, CreditRole.id == AlbumCredit.role_id
        ),
    ).subquery("album_role")


def album_card_columns() -> list[Any]:
    """The columns of `ArtistAlbum` except `roles`."""
    track_count = (
        select(func.count())
        .where(AlbumTrack.album_id == Album.id)
        .correlate(Album)
        .scalar_subquery()
    )
    # An album nobody is listed on (only credits) would give NULL, not an empty list.
    empty: ColumnElement[Any] = literal_column("'{}'")
    artists = (
        select(func.array_agg(aggregate_order_by(Artist.base_name, AlbumArtist.position)))
        .select_from(AlbumArtist)
        .join(Artist, Artist.id == AlbumArtist.artist_id)
        .where(AlbumArtist.album_id == Album.id)
        .correlate(Album)
        .scalar_subquery()
    )
    labels = (
        select(func.array_agg(aggregate_order_by(Artist.base_name, Artist.base_name)))
        .select_from(AlbumCredit)
        .join(CreditRole, CreditRole.id == AlbumCredit.role_id)
        .join(Artist, Artist.id == AlbumCredit.artist_id)
        .where(AlbumCredit.album_id == Album.id, CreditRole.name == "Label")
        .correlate(Album)
        .scalar_subquery()
    )
    return [
        Album.id,
        Album.genius_id,
        Album.base_name,
        Album.variant,
        Album.album_type,
        Album.release_date,
        Album.release_date_precision,
        Album.is_released,
        Album.cover_url,
        Album.genius_url,
        track_count.label("tracks_count"),
        Album.import_state,
        func.coalesce(artists, empty).label("artists"),
        func.coalesce(labels, empty).label("labels"),
    ]
