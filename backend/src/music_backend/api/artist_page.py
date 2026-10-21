"""Everything the artist page shows (a test feature, like the artist list: it stands on its own).

One call for the artist and its summaries, and paged calls for the two long lists. A song or an album
is related to an artist by a *role* (see `queries.py`).
"""

from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import Subquery, distinct, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.queries import (
    album_card_columns,
    album_roles,
    count,
    description_tree,
    get_or_404,
    imports_and_history,
    ordering,
    producers_of,
    raw_of,
    song_roles,
)
from music_backend.api.schemas import (
    ArtistAlbum,
    ArtistName,
    ArtistRef,
    ChangeOut,
    DomNode,
    DomRef,
    ImportRef,
    Page,
    PagingDep,
    RolesQuery,
)
from music_backend.bio import parse_bio
from music_backend.enums import ArtistType, DatePrecision, ImportKind, ImportState, SongArtistRole
from music_backend.models import (
    Album,
    AlbumTrack,
    Artist,
    ArtistAlias,
    ArtistMember,
    GeniusResponse,
    Genre,
    Song,
    SongArtist,
    SongVideo,
)

router = APIRouter(prefix="/api/v1/artists", tags=["artist page"])


class WorkRoleCount(BaseModel):
    role: str
    works: int


class GenreCount(BaseModel):
    genre: str
    songs: int


class PartialDateOut(BaseModel):
    date: date
    precision: DatePrecision


class ProfileLink(BaseModel):
    kind: str  # a key of Genius `social_links`: instagram, spotify, ...
    url: str


# Genius gives these as bare handles; the other keys are full URLs. Order is the order of the page.
_HANDLE_URLS = {
    "instagram": "https://instagram.com/{}",
    "x": "https://x.com/{}",
    "facebook": "https://facebook.com/{}",
    "tiktok": "https://tiktok.com/@{}",
    "snapchat": "https://snapchat.com/add/{}",
}
_LINK_ORDER = (
    "website", "spotify", "apple_music", "youtube", "soundcloud", "bandcamp", "tidal",
    "amazon_music", "shazam", *_HANDLE_URLS,
)  # fmt: skip


def _profile_links(social_links: dict[str, str]) -> list[ProfileLink]:
    # 503 of the stored artists have a key with an empty string: that is "no link".
    return [
        ProfileLink(kind=kind, url=_HANDLE_URLS.get(kind, "{}").format(social_links[kind]))
        for kind in _LINK_ORDER
        if social_links.get(kind)
    ]


class ArtistCore(BaseModel):
    id: int
    genius_id: int | None
    name: str
    base_name: str
    disambiguator: str | None
    artist_type: ArtistType | None
    import_state: ImportState
    description: str | None
    genius_url: str | None
    cover_url: str | None
    is_verified: bool | None
    is_meme_verified: bool | None
    followers_count: int | None
    created_at: datetime
    updated_at: datetime


class ArtistDetail(ArtistCore):
    description_dom: DomNode | None  # the description as Genius writes it, see `DomNode`
    description_refs: list[DomRef]
    real_name: str | None  # read from the start of the description, see `bio.py`
    born: PartialDateOut | None
    died: PartialDateOut | None
    links: list[ProfileLink]
    aliases: list[str]
    members: list[ArtistRef]  # of a group
    groups: list[ArtistRef]  # the artist belongs to
    songs_count: int
    albums_count: int
    song_roles: list[WorkRoleCount]
    album_roles: list[WorkRoleCount]
    genres: list[GenreCount]
    imports: list[ImportRef]
    history: list[ChangeOut]


class ArtistSong(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    variant: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    cover_thumbnail_url: str | None
    genius_url: str | None
    view_count: int | None
    genre: str | None
    album: str | None  # the primary album of the song
    import_state: ImportState
    roles: list[str]
    producers: list[ArtistName]  # credited as "Producer"


class ArtistVideo(BaseModel):
    song_id: int
    song_name: str
    variant: str | None
    url: str
    start_seconds: int | None
    explicit: bool
    official: bool
    release_date: date | None  # of the song
    release_date_precision: DatePrecision | None
    view_count: int | None  # of the song
    artists: list[str]  # the main artists of the song


def _of(roles: Subquery, artist_id: int, work: str) -> Subquery:
    """(work id, role) of one artist."""
    return select(roles.c[work], roles.c.role).where(roles.c.artist_id == artist_id).subquery()


async def _role_counts(session: AsyncSession, roles: Subquery, key: str) -> list[WorkRoleCount]:
    count = func.count(distinct(roles.c[key]))
    rows = await session.execute(
        select(roles.c.role, count).group_by(roles.c.role).order_by(count.desc(), roles.c.role)
    )
    return [WorkRoleCount(role=role, works=works) for role, works in rows]


async def _related(
    session: AsyncSession, column: Any, other: Any, artist_id: int
) -> list[ArtistRef]:
    """The artists on the other side of the membership links of this one."""
    rows = await session.scalars(
        select(Artist)
        .join(ArtistMember, other == Artist.id)
        .where(column == artist_id)
        .order_by(ArtistMember.position.nulls_last(), func.lower(Artist.base_name))
    )
    return [ArtistRef.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{artist_id}")
async def get_artist(artist_id: int, session: SessionDep, _: UserDep) -> ArtistDetail:
    artist = await get_or_404(session, Artist, artist_id)
    songs = _of(song_roles(), artist_id, "song_id")
    albums = _of(album_roles(), artist_id, "album_id")
    aliases = await session.scalars(
        select(ArtistAlias.name)
        .where(ArtistAlias.artist_id == artist_id)
        .order_by(ArtistAlias.name)
    )
    genre_count = func.count(distinct(Song.id))
    genres = await session.execute(
        select(Genre.name, genre_count)
        .join(Song, Song.genre_id == Genre.id)
        .where(Song.id.in_(select(songs.c.song_id)))
        .group_by(Genre.name)
        .order_by(genre_count.desc(), Genre.name)
        .limit(12)
    )
    imports, history = await imports_and_history(
        session, "artist", artist_id, artist.genius_id, [ImportKind.DISCOGRAPHY, ImportKind.ARTIST]
    )
    dom, refs = await description_tree(session, "artist", artist_id, ("description", "dom"))
    bio = parse_bio(artist.description)
    social_links = await session.scalar(
        select(GeniusResponse.raw["social_links"]).where(raw_of("artist", artist_id))
    )
    return ArtistDetail(
        **ArtistCore.model_validate(artist, from_attributes=True).model_dump(),
        description_dom=dom,
        description_refs=refs,
        real_name=bio.real_name if bio else None,
        born=PartialDateOut(date=bio.born[0], precision=bio.born[1]) if bio else None,
        died=PartialDateOut(date=bio.died[0], precision=bio.died[1]) if bio and bio.died else None,
        links=_profile_links(social_links) if social_links else [],
        aliases=list(aliases),
        members=await _related(session, ArtistMember.group_id, ArtistMember.member_id, artist_id),
        groups=await _related(session, ArtistMember.member_id, ArtistMember.group_id, artist_id),
        songs_count=await count(session, select(songs.c.song_id).distinct()),
        albums_count=await count(session, select(albums.c.album_id).distinct()),
        song_roles=await _role_counts(session, songs, "song_id"),
        album_roles=await _role_counts(session, albums, "album_id"),
        genres=[GenreCount(genre=name, songs=count_) for name, count_ in genres],
        imports=imports,
        history=history,
    )


@router.get("/{artist_id}/raw")
async def get_artist_raw(artist_id: int, session: SessionDep, _: UserDep) -> dict[str, Any] | None:
    """The untouched Genius response the artist was last imported from (null for a stub)."""
    await get_or_404(session, Artist, artist_id)
    return await session.scalar(select(GeniusResponse.raw).where(raw_of("artist", artist_id)))


@router.get("/{artist_id}/songs")
async def list_artist_songs(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    sort: Literal["name", "released", "views"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistSong]:
    """Songs the artist is on in any role; with `roles` only those where it has every one of them."""
    await get_or_404(session, Artist, artist_id)
    role = _of(song_roles(), artist_id, "song_id")
    all_roles = array_agg(distinct(role.c.role))  # type: ignore[no-untyped-call]  # untyped upstream
    having = [all_roles.contains(roles)] if roles else []
    album = (
        select(Album.base_name)
        .join(AlbumTrack, AlbumTrack.album_id == Album.id)
        .where(AlbumTrack.song_id == Song.id)
        .order_by(AlbumTrack.is_primary.desc().nulls_last(), AlbumTrack.id)
        .limit(1)
        .correlate(Song)
        .scalar_subquery()
    )
    name_key = func.lower(Song.base_name)
    keys = {
        "name": (name_key, "asc"),
        "released": (Song.release_date, "desc"),
        "views": (Song.view_count, "desc"),
    }

    rows = await session.execute(
        select(
            Song.id,
            Song.genius_id,
            Song.base_name,
            Song.variant,
            Song.release_date,
            Song.release_date_precision,
            Song.cover_thumbnail_url,
            Song.genius_url,
            Song.view_count,
            Genre.name.label("genre"),
            album.label("album"),
            Song.import_state,
            all_roles.label("roles"),
        )
        .join(role, role.c.song_id == Song.id)
        .outerjoin(Genre, Genre.id == Song.genre_id)
        .group_by(Song.id, Genre.name)
        .having(*having)
        .order_by(ordering(keys, sort, order), name_key, Song.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = select(role.c.song_id).group_by(role.c.song_id).having(*having)
    songs = rows.all()
    producers = await producers_of(session, [row.id for row in songs])
    return Page.of(
        [ArtistSong(**row._mapping, producers=producers.get(row.id, [])) for row in songs],
        await count(session, matching),
        paging,
    )


@router.get("/{artist_id}/videos")
async def list_artist_videos(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    sort: Literal["name", "released", "views"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistVideo]:
    """The clips Genius links from the songs the artist is on in any role, each address once."""
    await get_or_404(session, Artist, artist_id)
    role = _of(song_roles(), artist_id, "song_id")
    artists = (
        select(
            func.array_agg(aggregate_order_by(Artist.base_name, SongArtist.position.nulls_last()))
        )
        .select_from(SongArtist)
        .join(Artist, Artist.id == SongArtist.artist_id)
        .where(SongArtist.song_id == Song.id, SongArtist.role == SongArtistRole.PRIMARY)
        .correlate(Song)
        .scalar_subquery()
    )
    # A clip shared by several songs of the artist is shown once, with the song that came first.
    first = func.row_number().over(partition_by=SongVideo.url, order_by=Song.id).label("first")
    base = (
        select(
            Song.id.label("song_id"),
            Song.base_name.label("song_name"),
            Song.variant,
            SongVideo.url,
            SongVideo.start_seconds,
            SongVideo.explicit,
            SongVideo.official,
            Song.release_date,
            Song.release_date_precision,
            Song.view_count,
            artists.label("artists"),
            first,
        )
        .join(SongVideo, SongVideo.song_id == Song.id)
        .where(Song.id.in_(select(role.c.song_id)))
        .subquery()
    )
    keys = {
        "name": (func.lower(base.c.song_name), "asc"),
        "released": (base.c.release_date, "desc"),
        "views": (base.c.view_count, "desc"),
    }
    rows = await session.execute(
        select(base)
        .where(base.c.first == 1)
        .order_by(ordering(keys, sort, order), func.lower(base.c.song_name), base.c.song_id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = select(base.c.url).where(base.c.first == 1)
    return Page.of(
        [ArtistVideo(**{**row._mapping, "artists": row.artists or []}) for row in rows],
        await count(session, matching),
        paging,
    )


@router.get("/{artist_id}/albums")
async def list_artist_albums(
    artist_id: int,
    paging: PagingDep,
    session: SessionDep,
    _: UserDep,
    roles: RolesQuery,
    include_unreleased: bool = False,
    sort: Literal["name", "released"] = "released",
    order: Literal["asc", "desc"] | None = None,
) -> Page[ArtistAlbum]:
    """Albums the artist is on in any role (main or credited); `roles` as for the songs. Albums that are
    not out yet are left out unless `include_unreleased` is set."""
    await get_or_404(session, Artist, artist_id)
    role = _of(album_roles(), artist_id, "album_id")
    all_roles = array_agg(distinct(role.c.role))  # type: ignore[no-untyped-call]  # untyped upstream
    having = [all_roles.contains(roles)] if roles else []
    # A stub has NULL (unknown) and counts as released.
    filters = [] if include_unreleased else [Album.is_released.is_not(False)]
    name_key = func.lower(Album.base_name)
    keys = {"name": (name_key, "asc"), "released": (Album.release_date, "desc")}

    rows = await session.execute(
        select(*album_card_columns(), all_roles.label("roles"))
        .join(role, role.c.album_id == Album.id)
        .where(*filters)
        .group_by(Album.id)
        .having(*having)
        .order_by(ordering(keys, sort, order), name_key, Album.id)
        .limit(paging.limit)
        .offset(paging.offset)
    )
    matching = (
        select(role.c.album_id)
        .join(Album, Album.id == role.c.album_id)
        .where(*filters)
        .group_by(role.c.album_id)
        .having(*having)
    )
    return Page.of(
        [ArtistAlbum(**row._mapping) for row in rows], await count(session, matching), paging
    )
