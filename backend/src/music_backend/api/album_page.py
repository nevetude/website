"""Everything the album page shows: the album with its summaries, the tracklist and the raw response.

The server gives facts and a stable order; how a track number or a relation is worded is the client's
decision.
"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import SessionDep, UserDep
from music_backend.api.queries import (
    album_cards,
    count,
    description_tree,
    get_or_404,
    imports_and_history,
    producers_of,
    raw_of,
)
from music_backend.api.schemas import (
    ArtistAlbum,
    ArtistName,
    ArtistRef,
    ChangeOut,
    DomNode,
    DomRef,
    ImportRef,
)
from music_backend.enums import (
    AlbumRelationType,
    DatePrecision,
    ImportKind,
    ImportState,
    SongArtistRole,
)
from music_backend.models import (
    Album,
    AlbumArtist,
    AlbumCoverArt,
    AlbumCredit,
    AlbumRelationship,
    AlbumTrack,
    Artist,
    CreditRole,
    GeniusResponse,
    Genre,
    Song,
    SongArtist,
    SongCredit,
    SongVideo,
)

router = APIRouter(prefix="/api/v1/albums", tags=["album page"])


class CoverOut(BaseModel):
    id: int
    image_url: str
    thumbnail_image_url: str
    genius_url: str
    explicit: bool


class CreditArtist(BaseModel):
    artist: ArtistRef
    tracks: (
        int | None
    )  # tracks of this album with the credit; null for a credit of the album itself


class CreditGroup(BaseModel):
    role: str
    from_album: (
        bool  # given for the album as a whole (Label, Copyright, ...), not summed up from its songs
    )
    artists: list[CreditArtist]


class RelatedAlbums(BaseModel):
    """`inverse` false: this album *is* the type of the others ("deluxe edition of"); true: the others
    are the type of this one ("deluxe editions")."""

    type: AlbumRelationType
    inverse: bool
    albums: list[ArtistAlbum]


class AlbumCore(BaseModel):
    id: int
    genius_id: int | None
    name: str
    base_name: str
    variant: str | None
    disambiguator: str | None
    album_type: str | None
    import_state: ImportState
    language: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    is_released: bool | None
    description: str | None
    genius_url: str | None
    cover_url: str | None
    cover_primary_color: str | None
    cover_secondary_color: str | None
    created_at: datetime
    updated_at: datetime


class AlbumDetail(AlbumCore):
    description_dom: DomNode | None  # the description as Genius writes it, see `DomNode`
    description_refs: list[DomRef]
    artists: list[ArtistRef]
    covers: list[CoverOut]  # every cover Genius knows; the main one is `cover_url`
    tracks_count: int
    discs_count: int
    genres: list[str]  # of its songs, the most common first
    credits: list[CreditGroup]
    related: list[RelatedAlbums]
    imports: list[ImportRef]
    history: list[ChangeOut]


class AlbumVideoOut(BaseModel):
    song_id: int
    song_name: str
    url: str
    start_seconds: int | None
    explicit: bool
    official: bool
    release_date: date | None  # of the song, with the precision Genius has
    release_date_precision: DatePrecision | None


class AlbumTrackOut(BaseModel):
    id: int  # of the placement
    song_id: int
    disc_number: int | None
    position: int | None
    base_name: str
    variant: str | None
    genius_url: str | None
    cover_thumbnail_url: str | None
    import_state: ImportState
    explicit: bool | None
    view_count: int | None
    is_primary: bool | None  # the song's primary album is this one
    artists: list[ArtistName]
    featured: list[ArtistName]
    producers: list[ArtistName]  # credited as "Producer", in the order they were imported


async def _related(session: AsyncSession, album_id: int) -> list[RelatedAlbums]:
    rows = (
        await session.execute(
            select(AlbumRelationship).where(
                (AlbumRelationship.album_id == album_id)
                | (AlbumRelationship.related_album_id == album_id)
            )
        )
    ).scalars()
    found: dict[tuple[AlbumRelationType, bool], list[int]] = {}
    for row in rows:
        inverse = row.related_album_id == album_id
        other = row.album_id if inverse else row.related_album_id
        found.setdefault((row.type, inverse), []).append(other)
    cards = await album_cards(session, [i for ids in found.values() for i in ids])
    return [
        RelatedAlbums(
            type=kind,
            inverse=inverse,
            albums=sorted(
                (cards[i] for i in ids),
                key=lambda a: (a.release_date is None, a.release_date or date.min, a.id),
                reverse=True,
            ),
        )
        for (kind, inverse), ids in sorted(found.items())
    ]


async def _genres(session: AsyncSession, album_id: int) -> list[str]:
    songs = func.count()
    rows = await session.scalars(
        select(Genre.name)
        .join(Song, Song.genre_id == Genre.id)
        .join(AlbumTrack, AlbumTrack.song_id == Song.id)
        .where(AlbumTrack.album_id == album_id)
        .group_by(Genre.name)
        .order_by(songs.desc(), Genre.name)
        .limit(5)
    )
    return list(rows)


async def _credits(session: AsyncSession, album_id: int) -> list[CreditGroup]:
    """The credits of the album itself, then the credits of its songs summed up by role."""
    own = await session.execute(
        select(Artist, CreditRole.name)
        .select_from(AlbumCredit)
        .join(Artist, Artist.id == AlbumCredit.artist_id)
        .join(CreditRole, CreditRole.id == AlbumCredit.role_id)
        .where(AlbumCredit.album_id == album_id)
    )
    songs = await session.execute(
        select(Artist, CreditRole.name, func.count(distinct(AlbumTrack.song_id)))
        .select_from(AlbumTrack)
        .join(SongCredit, SongCredit.song_id == AlbumTrack.song_id)
        .join(Artist, Artist.id == SongCredit.artist_id)
        .join(CreditRole, CreditRole.id == SongCredit.role_id)
        .where(AlbumTrack.album_id == album_id)
        .group_by(Artist.id, CreditRole.name)
    )
    # One group per role: the same role can be given for the album and for its songs (the Label of both).
    groups: dict[str, dict[int, CreditArtist]] = {}
    from_album: set[str] = set()
    for artist, role in own:
        from_album.add(role)
        groups.setdefault(role, {})[artist.id] = CreditArtist(
            artist=ArtistRef.model_validate(artist, from_attributes=True), tracks=None
        )
    for artist, role, tracks in songs:
        groups.setdefault(role, {})[artist.id] = CreditArtist(
            artist=ArtistRef.model_validate(artist, from_attributes=True), tracks=tracks
        )
    ordered = sorted(groups.items(), key=lambda g: (g[0] not in from_album, -len(g[1]), g[0]))
    return [
        CreditGroup(
            role=role,
            from_album=role in from_album,
            artists=sorted(
                members.values(),
                key=lambda c: (-(c.tracks or 0), c.artist.base_name.lower()),
            ),
        )
        for role, members in ordered
    ]


@router.get("/{album_id}")
async def get_album(album_id: int, session: SessionDep, _: UserDep) -> AlbumDetail:
    album = await get_or_404(session, Album, album_id)
    artists = await session.scalars(
        select(Artist)
        .join(AlbumArtist, AlbumArtist.artist_id == Artist.id)
        .where(AlbumArtist.album_id == album_id)
        .order_by(AlbumArtist.position.nulls_last(), Artist.base_name)
    )
    covers = await session.scalars(
        select(AlbumCoverArt)
        .where(AlbumCoverArt.album_id == album_id)
        .order_by(AlbumCoverArt.position)
    )
    tracks = select(AlbumTrack).where(AlbumTrack.album_id == album_id)
    discs = select(func.coalesce(AlbumTrack.disc_number, 1)).where(AlbumTrack.album_id == album_id)
    dom, refs = await description_tree(
        session,
        "album",
        album_id,
        ("description_annotation", "annotations", 0, "body", "dom"),
    )
    imports, history = await imports_and_history(
        session, "album", album_id, album.genius_id, [ImportKind.ALBUM]
    )
    return AlbumDetail(
        **AlbumCore.model_validate(album, from_attributes=True).model_dump(),
        description_dom=dom,
        description_refs=refs,
        artists=[ArtistRef.model_validate(a, from_attributes=True) for a in artists],
        covers=[CoverOut.model_validate(c, from_attributes=True) for c in covers],
        tracks_count=await count(session, tracks),
        discs_count=await count(session, discs.distinct()),
        genres=await _genres(session, album_id),
        credits=await _credits(session, album_id),
        related=await _related(session, album_id),
        imports=imports,
        history=history,
    )


@router.get("/{album_id}/tracks")
async def list_album_tracks(album_id: int, session: SessionDep, _: UserDep) -> list[AlbumTrackOut]:
    """The tracklist in order: by disc, then by position (when Genius has none, by order of arrival)."""
    await get_or_404(session, Album, album_id)
    rows = (
        await session.execute(
            select(AlbumTrack, Song)
            .join(Song, Song.id == AlbumTrack.song_id)
            .where(AlbumTrack.album_id == album_id)
            .order_by(
                func.coalesce(AlbumTrack.disc_number, 1),
                AlbumTrack.position.nulls_last(),
                AlbumTrack.sort_order.nulls_last(),
                AlbumTrack.id,
            )
        )
    ).all()
    credited = await session.execute(
        select(SongArtist.song_id, SongArtist.role, Artist.id, Artist.base_name)
        .join(Artist, Artist.id == SongArtist.artist_id)
        .where(SongArtist.song_id.in_([song.id for _, song in rows]))
        .order_by(SongArtist.position.nulls_last(), Artist.base_name)
    )
    producers = await producers_of(session, [song.id for _, song in rows])
    primary: dict[int, list[ArtistName]] = {}
    featured: dict[int, list[ArtistName]] = {}
    for song_id, role, artist_id, name in credited:
        target = primary if role is SongArtistRole.PRIMARY else featured
        target.setdefault(song_id, []).append(ArtistName(id=artist_id, base_name=name))
    return [
        AlbumTrackOut(
            id=track.id,
            song_id=song.id,
            disc_number=track.disc_number,
            position=track.position,
            base_name=song.base_name,
            variant=song.variant,
            genius_url=song.genius_url,
            cover_thumbnail_url=song.cover_thumbnail_url,
            import_state=song.import_state,
            explicit=song.explicit,
            view_count=song.view_count,
            is_primary=track.is_primary,
            artists=primary.get(song.id, []),
            featured=featured.get(song.id, []),
            producers=producers.get(song.id, []),
        )
        for track, song in rows
    ]


@router.get("/{album_id}/videos")
async def list_album_videos(album_id: int, session: SessionDep, _: UserDep) -> list[AlbumVideoOut]:
    """The clips Genius links from the songs of the album, in the order of the tracklist, each address once."""
    await get_or_404(session, Album, album_id)
    rows = await session.execute(
        select(SongVideo, Song)
        .join(Song, Song.id == SongVideo.song_id)
        .join(AlbumTrack, AlbumTrack.song_id == Song.id)
        .where(AlbumTrack.album_id == album_id)
        .order_by(
            func.coalesce(AlbumTrack.disc_number, 1),
            AlbumTrack.position.nulls_last(),
            AlbumTrack.sort_order.nulls_last(),
            AlbumTrack.id,
            SongVideo.id,
        )
    )
    videos: dict[str, AlbumVideoOut] = {}
    for link, song in rows:
        videos.setdefault(
            link.url,
            AlbumVideoOut(
                song_id=song.id,
                song_name=song.base_name,
                url=link.url,
                start_seconds=link.start_seconds,
                explicit=link.explicit,
                official=link.official,
                release_date=song.release_date,
                release_date_precision=song.release_date_precision,
            ),
        )
    return list(videos.values())


@router.get("/{album_id}/raw")
async def get_album_raw(album_id: int, session: SessionDep, _: UserDep) -> dict[str, Any] | None:
    """The untouched Genius response the album was last imported from (null for a stub)."""
    await get_or_404(session, Album, album_id)
    return await session.scalar(select(GeniusResponse.raw).where(raw_of("album", album_id)))
