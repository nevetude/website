from datetime import date

from sqlalchemy import BigInteger, false
from sqlalchemy.orm import Mapped, mapped_column

from music_backend.enums import (
    AlbumRelationType,
    AlbumType,
    ArtistType,
    DatePrecision,
    SongArtistRole,
    SongRelationType,
)
from music_backend.models.base import (
    ORDER_EXTERNAL_ID,
    ORDER_NAME,
    ORDER_TYPE,
    Base,
    GeniusEntity,
    IdMixin,
    Named,
    Timestamps,
    enum_column,
    fk,
)

# Trust the data: no CHECK constraints and no business-rule indexes here. Only keys, NOT NULL and the
# uniqueness the code looks things up by (genius_id, dictionary names, file path).


# --- dictionaries ---------------------------------------------------------------------------------


class Genre(Base, IdMixin, Timestamps, Named):
    __tablename__ = "genre"

    genius_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, sort_order=ORDER_EXTERNAL_ID
    )


class Tag(Base, IdMixin, Timestamps, Named):
    __tablename__ = "tag"

    genius_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, sort_order=ORDER_EXTERNAL_ID
    )


class CreditRole(Base, IdMixin):
    __tablename__ = "credit_role"

    name: Mapped[str] = mapped_column(unique=True)


# --- artist -----------------------------------------------------------------------------------------


class Artist(Base, IdMixin, Timestamps, GeniusEntity, Named):
    __tablename__ = "artist"

    # NULL for a stub that nobody called a group: Genius does not say what it is.
    artist_type: Mapped[ArtistType | None] = enum_column(
        ArtistType, nullable=True, sort_order=ORDER_TYPE
    )
    description: Mapped[str | None]
    genius_url: Mapped[str | None]
    cover_url: Mapped[str | None]
    is_verified: Mapped[bool | None]
    is_meme_verified: Mapped[bool | None]
    followers_count: Mapped[int | None]
    # `social_links` is not stored: the artist page reads it from the raw response (docs/parked-fields.md).


class ArtistAlias(Base, IdMixin):
    """Alternative names (Aphex Twin: AFX, Polygon Window, ...). Import only adds, never removes."""

    __tablename__ = "artist_alias"

    artist_id: Mapped[int] = fk("artist")
    name: Mapped[str]


class ArtistMember(Base):
    __tablename__ = "artist_member"

    group_id: Mapped[int] = fk("artist", primary_key=True)
    member_id: Mapped[int] = fk("artist", primary_key=True, index=True)
    position: Mapped[int | None]


# --- album ------------------------------------------------------------------------------------------


class Album(Base, IdMixin, Timestamps, GeniusEntity, Named):
    __tablename__ = "album"

    variant: Mapped[str | None] = mapped_column(sort_order=ORDER_NAME + 1)
    album_type: Mapped[AlbumType | None] = enum_column(
        AlbumType, nullable=True, sort_order=ORDER_TYPE
    )
    language: Mapped[str | None]
    # Genius pads unknown parts with 1 (2010-01-01 for "2010"); the precision says how much is real.
    release_date: Mapped[date | None]
    release_date_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    # NULL for stubs: nothing is known about them yet.
    is_released: Mapped[bool | None]
    description: Mapped[str | None]
    genius_url: Mapped[str | None]
    cover_url: Mapped[str | None]
    cover_thumbnail_url: Mapped[str | None]
    cover_primary_color: Mapped[str | None]
    cover_secondary_color: Mapped[str | None]
    # Parked, not stored (see docs/parked-fields.md): counters, song_pageviews, updated_at, hidden, lock_state, ...


class AlbumArtist(Base):
    __tablename__ = "album_artist"

    album_id: Mapped[int] = fk("album", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True, index=True)
    position: Mapped[int | None]


class AlbumRelationship(Base, IdMixin):
    """Stored in one direction only; the inverse side is derived."""

    __tablename__ = "album_relationship"

    album_id: Mapped[int] = fk("album")
    related_album_id: Mapped[int] = fk("album", index=True)
    type: Mapped[AlbumRelationType] = enum_column(AlbumRelationType)


class AlbumCredit(Base, IdMixin):
    __tablename__ = "album_credit"

    album_id: Mapped[int] = fk("album", index=True)
    artist_id: Mapped[int] = fk("artist", index=True)
    role_id: Mapped[int] = fk("credit_role")
    label_text: Mapped[str | None]  # the role label exactly as the source wrote it


class AlbumCoverArt(Base, IdMixin):
    """Every cover Genius knows for the album (the main one is also `album.cover_url`)."""

    __tablename__ = "album_cover_art"

    genius_id: Mapped[int] = mapped_column(BigInteger, unique=True, sort_order=ORDER_EXTERNAL_ID)
    album_id: Mapped[int] = fk("album", index=True)
    position: Mapped[int]
    # Set by hand, never by the import.
    explicit: Mapped[bool] = mapped_column(default=False, server_default=false())
    image_url: Mapped[str]
    thumbnail_image_url: Mapped[str]
    genius_url: Mapped[str]


class AlbumFolder(Base, IdMixin):
    __tablename__ = "album_folder"

    album_id: Mapped[int] = fk("album")
    path: Mapped[str]


# --- song -------------------------------------------------------------------------------------------


class Song(Base, IdMixin, Timestamps, GeniusEntity, Named):
    __tablename__ = "song"

    variant: Mapped[str | None] = mapped_column(sort_order=ORDER_NAME + 1)
    language: Mapped[str | None]
    # Genius pads unknown parts with 1; the precision says how much is real (see Album).
    release_date: Mapped[date | None]
    release_date_precision: Mapped[DatePrecision | None] = enum_column(DatePrecision, nullable=True)
    description: Mapped[str | None]
    recording_location: Mapped[str | None]
    # NULL until the song is imported in full: a stub does not know them.
    explicit: Mapped[bool | None]
    instrumental: Mapped[bool | None]
    is_music: Mapped[bool | None]
    hidden: Mapped[bool | None]
    published: Mapped[bool | None]
    lyrics_state: Mapped[str | None]  # Genius value: complete, incomplete, unreleased
    genre_id: Mapped[int | None] = fk("genre", nullable=True, index=True)
    genius_url: Mapped[str | None]
    cover_url: Mapped[str | None]
    cover_thumbnail_url: Mapped[str | None]
    cover_primary_color: Mapped[str | None]
    cover_secondary_color: Mapped[str | None]
    view_count: Mapped[int | None]  # Genius stats.pageviews; the other counters are parked


class SongAudio(Base, IdMixin):
    """A place where the song can be heard (Genius `media[]` that is not a video: SoundCloud, Spotify). Not a local file:
    see MediaFile. The videos are in `song_video`."""

    __tablename__ = "song_audio"

    song_id: Mapped[int] = fk("song", index=True)
    provider: Mapped[str]  # soundcloud, spotify
    url: Mapped[str]
    native_uri: Mapped[str | None]
    attribution: Mapped[str | None]


class SongVideo(Base, IdMixin):
    """A YouTube video of the song (Genius `media[]` of type video: the importer takes every one of them for YouTube)."""

    __tablename__ = "song_video"

    song_id: Mapped[int] = fk("song", index=True)
    # Set by hand (a clip with explicit content), never by the import.
    explicit: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Set by hand: the official clip of the artist, not just the audio put on YouTube.
    official: Mapped[bool] = mapped_column(default=False, server_default=false())
    url: Mapped[str]
    start_seconds: Mapped[int | None]


class SongArtist(Base):
    __tablename__ = "song_artist"

    song_id: Mapped[int] = fk("song", primary_key=True)
    artist_id: Mapped[int] = fk("artist", primary_key=True, index=True)
    role: Mapped[SongArtistRole] = enum_column(SongArtistRole, primary_key=True)
    position: Mapped[int | None]


class SongTag(Base):
    __tablename__ = "song_tag"

    song_id: Mapped[int] = fk("song", primary_key=True)
    tag_id: Mapped[int] = fk("tag", primary_key=True, index=True)


class SongCredit(Base, IdMixin):
    __tablename__ = "song_credit"

    song_id: Mapped[int] = fk("song", index=True)
    artist_id: Mapped[int] = fk("artist", index=True)
    role_id: Mapped[int] = fk("credit_role")
    label_text: Mapped[str | None]  # the role label exactly as the source wrote it


class SongRelationship(Base, IdMixin):
    """Stored in one direction only; the inverse side is derived."""

    __tablename__ = "song_relationship"

    song_id: Mapped[int] = fk("song")
    related_song_id: Mapped[int] = fk("song", index=True)
    type: Mapped[SongRelationType] = enum_column(SongRelationType)


# --- placement of a song on an album -----------------------------------------------------------------


class AlbumTrack(Base, IdMixin):
    __tablename__ = "album_track"

    album_id: Mapped[int] = fk("album", index=True)
    song_id: Mapped[int] = fk("song", index=True)
    # The song import knows the album but not the numbers, the album import knows the numbers but not
    # whether this is the primary album: each fills in only its part, the rest stays NULL.
    disc_number: Mapped[int | None]
    position: Mapped[int | None]  # Genius often has none
    sort_order: Mapped[int | None]  # order of arrival; fallback when position is missing
    is_primary: Mapped[bool | None]


class MediaFile(Base, IdMixin, Timestamps):
    __tablename__ = "media_file"

    album_track_id: Mapped[int] = fk("album_track", index=True)
    path: Mapped[str] = mapped_column(unique=True)
    format: Mapped[str]
    duration_ms: Mapped[int | None]
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str | None]
