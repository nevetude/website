from sqlalchemy import ForeignKey, SmallInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from music_backend.models.base import Base, IdMixin, Timestamps, fk

# Lyrics and annotations are placeholders: tables exist, no import or display logic yet.


class Lyrics(Base, IdMixin, Timestamps):
    __tablename__ = "lyrics"

    song_id: Mapped[int] = fk("song", unique=True)
    source: Mapped[str | None]
    is_synced: Mapped[bool] = mapped_column(server_default=text("false"))


class LyricLine(Base, IdMixin):
    """One line of text; start_ms/end_ms drive line switching during playback."""

    __tablename__ = "lyric_line"

    lyrics_id: Mapped[int] = mapped_column(ForeignKey("lyrics.id", ondelete="CASCADE"))
    position: Mapped[int]
    text: Mapped[str]
    start_ms: Mapped[int | None]
    end_ms: Mapped[int | None]


class Annotation(Base, IdMixin, Timestamps):
    __tablename__ = "annotation"

    song_id: Mapped[int] = fk("song", index=True)
    line_from: Mapped[int | None]
    line_to: Mapped[int | None]
    body: Mapped[str]
    source: Mapped[str | None]


# --- ratings and reviews (real tables, empty until users add some) ------------------------------------


class AlbumRating(Base, IdMixin, Timestamps):
    __tablename__ = "album_rating"

    user_id: Mapped[int] = fk("app_user")
    album_id: Mapped[int] = fk("album", index=True)
    score: Mapped[int] = mapped_column(SmallInteger)


class SongRating(Base, IdMixin, Timestamps):
    __tablename__ = "song_rating"

    user_id: Mapped[int] = fk("app_user")
    song_id: Mapped[int] = fk("song", index=True)
    score: Mapped[int] = mapped_column(SmallInteger)


class AlbumReview(Base, IdMixin, Timestamps):
    __tablename__ = "album_review"

    user_id: Mapped[int] = fk("app_user")
    album_id: Mapped[int] = fk("album", index=True)
    body: Mapped[str]


class SongReview(Base, IdMixin, Timestamps):
    __tablename__ = "song_review"

    user_id: Mapped[int] = fk("app_user")
    song_id: Mapped[int] = fk("song", index=True)
    body: Mapped[str]
