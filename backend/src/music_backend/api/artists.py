"""The artist list of the home page (a test feature: it may go away, so it stands on its own).

The server answers with facts and filters on facts; which of them make a "block" on the page is the
client's decision.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Subquery, distinct, exists, func, or_, select, union

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.queries import album_roles, count, ordering, song_roles
from music_backend.api.schemas import Page, PagingDep, RolesQuery
from music_backend.enums import ArtistType, ImportKind, ImportState, JobStatus
from music_backend.models import Artist, ImportJob, SongArtist

router = APIRouter(prefix="/api/v1/artists", tags=["artists"])


class ArtistFilters(BaseModel):
    import_state: ImportState | None = None
    is_group: bool | None = None
    # Whether a successful import of the artist's discography was run for it by hand.
    discography_imported: bool | None = None


class ArtistCard(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    cover_url: str | None
    genius_url: str | None
    is_verified: bool | None
    followers_count: int | None
    tracks_count: int  # songs on which the artist is a primary or a featured artist
    artist_type: ArtistType | None
    import_state: ImportState


class RoleCount(BaseModel):
    role: str
    artists: int


def _conditions(filters: ArtistFilters) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = []
    if filters.import_state is not None:
        where.append(Artist.import_state == filters.import_state)
    if filters.is_group is True:
        where.append(Artist.artist_type == ArtistType.GROUP)
    elif filters.is_group is False:
        where.append(or_(Artist.artist_type.is_(None), Artist.artist_type != ArtistType.GROUP))
    if filters.discography_imported is not None:
        imported = exists().where(
            ImportJob.kind == ImportKind.DISCOGRAPHY,
            ImportJob.status == JobStatus.SUCCEEDED,
            ImportJob.genius_id == Artist.genius_id,
        )
        where.append(imported if filters.discography_imported else ~imported)
    return where


def _artist_roles() -> Subquery:
    """(artist_id, role) for every role an artist has, in songs and in albums."""
    songs, albums = song_roles(), album_roles()
    return union(
        select(songs.c.artist_id, songs.c.role), select(albums.c.artist_id, albums.c.role)
    ).subquery("artist_role")


@router.get("")
async def list_artists(
    filters: Annotated[ArtistFilters, Depends()],
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    sort: Literal["name", "followers", "tracks"] = "name",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistCard]:
    """Artists matching all the filters and having every one of `roles` (all of them, not any)."""
    tracks = (
        select(func.count(distinct(SongArtist.song_id)))
        .where(SongArtist.artist_id == Artist.id)
        .correlate(Artist)
        .scalar_subquery()
    )
    artist_roles = _artist_roles()
    where = _conditions(filters)
    where += [
        exists().where(artist_roles.c.artist_id == Artist.id, artist_roles.c.role == role)
        for role in roles
    ]
    name_key = func.lower(Artist.base_name)
    keys = {
        "name": (name_key, "asc"),
        "followers": (Artist.followers_count, "desc"),
        "tracks": (tracks, "desc"),
    }

    rows = await session.execute(
        select(
            Artist.id,
            Artist.genius_id,
            Artist.base_name,
            Artist.cover_url,
            Artist.genius_url,
            Artist.is_verified,
            Artist.followers_count,
            tracks.label("tracks_count"),
            Artist.artist_type,
            Artist.import_state,
        )
        .where(*where)
        .order_by(ordering(keys, sort, order), name_key, Artist.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    total = await count(session, select(Artist.id).where(*where))
    return Page.of([ArtistCard(**row._mapping) for row in rows], total, paging)


@router.get("/roles")
async def list_artist_roles(
    filters: Annotated[ArtistFilters, Depends()],
    session: SessionDep,
    _: UserDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 40,
) -> list[RoleCount]:
    """The roles found among the artists matching the filters, the most common first."""
    artist_roles = _artist_roles()
    count = func.count(distinct(artist_roles.c.artist_id))
    rows = await session.execute(
        select(artist_roles.c.role, count.label("artists"))
        .join(Artist, Artist.id == artist_roles.c.artist_id)
        .where(*_conditions(filters))
        .group_by(artist_roles.c.role)
        .order_by(count.desc(), artist_roles.c.role)
        .limit(limit)
    )
    return [RoleCount(role=role, artists=artists) for role, artists in rows]
