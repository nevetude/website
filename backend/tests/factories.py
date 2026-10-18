from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.models import Album, AlbumTrack, AppUser, Artist, Song

_n = count(1)


async def make_artist(session: AsyncSession, name: str = "Artist", **kwargs: object) -> Artist:
    artist = Artist(name=name, base_name=name, **kwargs)
    session.add(artist)
    await session.flush()
    return artist


async def make_song(session: AsyncSession, name: str = "Song", **kwargs: object) -> Song:
    song = Song(name=name, base_name=name, **kwargs)
    session.add(song)
    await session.flush()
    return song


async def make_album(session: AsyncSession, name: str = "Album", **kwargs: object) -> Album:
    album = Album(name=name, base_name=name, **kwargs)
    session.add(album)
    await session.flush()
    return album


async def make_user(session: AsyncSession) -> AppUser:
    user = AppUser(login=f"user{next(_n)}", password_hash="x")
    session.add(user)
    await session.flush()
    return user


async def place(
    session: AsyncSession, album: Album, song: Song, position: int | None = None, **kwargs: object
) -> AlbumTrack:
    track = AlbumTrack(
        album_id=album.id, song_id=song.id, position=position, sort_order=next(_n), **kwargs
    )
    session.add(track)
    await session.flush()
    return track
