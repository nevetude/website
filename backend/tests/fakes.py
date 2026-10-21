"""A stand-in for Genius: payloads with every field the importers read, and a client that serves them."""

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.imports.client import GeniusError, Recorder
from music_backend.imports.common import Context, Task
from music_backend.imports.runner import Progress, run_tasks

# An artist keeps the name it was first listed with, so its own card agrees with the lists.
NAMES: dict[int, str] = {}


def person(genius_id: int, name: str | None = None) -> dict[str, Any]:
    """An artist as Genius lists it inside other objects."""
    if name:
        NAMES[genius_id] = name
    return {
        "id": genius_id,
        "name": NAMES.get(genius_id, f"Artist {genius_id}"),
        "image_url": f"https://img/{genius_id}.jpg",
    }


def artist_payload(
    genius_id: int,
    name: str | None = None,
    *,
    members: tuple[dict[str, Any], ...] = (),
    groups: tuple[dict[str, Any], ...] = (),
    **overrides: Any,
) -> dict[str, Any]:
    name = name or NAMES.get(genius_id, f"Artist {genius_id}")
    relations = []
    if members:
        relations.append({"relationship_type": "members", "artists": list(members)})
    if groups:
        relations.append({"relationship_type": "member_of", "artists": list(groups)})
    payload = {
        "id": genius_id,
        "name": name,
        "name_components": {"base_name": name, "disambiguator": None},
        "description": description("A bio"),
        "url": f"https://genius.com/artists/{genius_id}",
        "image_url": "https://img/a.jpg",
        "header_image_url": None,
        "is_verified": False,
        "is_meme_verified": False,
        "followers_count": 289,
        "alternate_names": [],
        "artist_relationships": relations,
    }
    return payload | overrides


def album_payload(genius_id: int, name: str | None = None, **overrides: Any) -> dict[str, Any]:
    payload = {
        "id": genius_id,
        "name": name or f"Album {genius_id}",
        "album_type": "album",
        "language": None,
        "release_date_components": {"year": 2020, "month": 5, "day": 17},
        "description_annotation": {"annotations": [{"body": description()}]},
        "url": f"https://genius.com/albums/{genius_id}",
        "cover_art_url": "https://img/cover.jpg",
        "cover_art_thumbnail_url": "https://img/thumb.jpg",
        "header_image_url": "https://img/header.jpg",
        "custom_header_image_url": None,
        "album_art_primary_color": "#111111",
        "album_art_secondary_color": "#222222",
        "comment_count": 0,
        "contributors_count": 1,
        "pyongs_count": 0,
        "primary_artists": [person(1)],
        "cover_arts": [],
        "performance_groups": [],
        "song_performances": [],
        "album_relationships": [],
    }
    return payload | overrides


def description(*paragraphs: str) -> dict[str, Any]:
    """A description as Genius writes it by default: a `dom` tree, a paragraph per text."""
    return {"dom": {"tag": "root", "children": [{"tag": "p", "children": [p]} for p in paragraphs]}}


def related_album(genius_id: int, name: str | None = None) -> dict[str, Any]:
    """An album as Genius lists it inside another album's relations."""
    return {
        "id": genius_id,
        "name": name or f"Album {genius_id}",
        "cover_art_url": "https://img/rel.jpg",
    }


def track(
    song_id: int, title: str | None = None, disc: int | None = 1, number: int | None = 1
) -> dict[str, Any]:
    return {
        "disc_number": disc,
        "disc_track_number": number,
        "number": number,
        "song": {"id": song_id, "title": title or f"Song {song_id}"},
    }


def song_payload(genius_id: int, title: str | None = None, **overrides: Any) -> dict[str, Any]:
    payload = {
        "id": genius_id,
        "title": title or f"Song {genius_id}",
        "language": "en",
        "release_date_components": {"year": 2020, "month": 5, "day": 17},
        "description": description(),
        "recording_location": None,
        "explicit": False,
        "instrumental": False,
        "is_music": True,
        "hidden": False,
        "published": True,
        "lyrics_state": "complete",
        "url": f"https://genius.com/songs/{genius_id}",
        "song_art_image_url": "https://img/art.jpg",
        "song_art_image_thumbnail_url": "https://img/art-thumb.jpg",
        "custom_song_art_image_url": None,
        "header_image_url": "https://img/header.jpg",
        "header_image_thumbnail_url": "https://img/header-thumb.jpg",
        "custom_header_image_url": None,
        "song_art_primary_color": "#111111",
        "song_art_secondary_color": "#222222",
        "stats": {"pageviews": 1000},
        "primary_tag": {"id": 1, "name": "Rap"},
        "tags": [{"id": 1, "name": "Rap"}],
        "primary_artists": [person(1)],
        "featured_artists": [],
        "writer_artists": [],
        "producer_artists": [],
        "custom_performances": [],
        "song_relationships": [],
        "media": [],
        "album": None,
        "albums": [],
    }
    return payload | overrides


class FakeGenius:
    """Serves payloads by Genius path. Unknown ids get default payloads; `missing` ids answer 404."""

    def __init__(
        self,
        *,
        artists: dict[int, dict[str, Any]] | None = None,
        albums: dict[int, dict[str, Any]] | None = None,
        tracks: dict[int, list[dict[str, Any]]] | None = None,
        songs: dict[int, dict[str, Any]] | None = None,
        discographies: dict[int, list[int]] | None = None,  # album ids, newest first
        missing: set[str] | None = None,  # paths like "/songs/7"
        page_size: int = 50,
    ) -> None:
        self.artists, self.albums, self.tracks = artists or {}, albums or {}, tracks or {}
        self.songs, self.discographies = songs or {}, discographies or {}
        self.missing, self.page_size = missing or set(), page_size
        self.calls: list[str] = []
        self.connection = None

    async def get(
        self, path: str, params: dict[str, Any] | None = None, record: Recorder | None = None
    ) -> dict[str, Any]:
        self.calls.append(path)
        if path in self.missing:
            raise GeniusError(f"Genius answered 404 for {path}", 404)
        if match := re.fullmatch(r"/artists/(\d+)/albums", path):
            ids = self.discographies.get(int(match[1]), [])
            page = (params or {}).get("page", 1)
            chunk = ids[(page - 1) * self.page_size : page * self.page_size]
            more = page * self.page_size < len(ids)
            return {
                "albums": [{"id": i, "name": f"Album {i}"} for i in chunk],
                "next_page": page + 1 if more else None,
            }
        if match := re.fullmatch(r"/artists/(\d+)", path):
            return {"artist": self.artists.get(int(match[1])) or artist_payload(int(match[1]))}
        if match := re.fullmatch(r"/albums/(\d+)/tracks", path):
            return {"tracks": self.tracks.get(int(match[1]), []), "next_page": None}
        if match := re.fullmatch(r"/albums/(\d+)", path):
            return {"album": self.albums.get(int(match[1])) or album_payload(int(match[1]))}
        if match := re.fullmatch(r"/songs/(\d+)", path):
            return {"song": self.songs.get(int(match[1])) or song_payload(int(match[1]))}
        raise AssertionError(f"unexpected Genius path {path}")


def snapshot(state: Progress) -> dict[str, Any]:
    """The progress as plain values, because the runner keeps changing the same object."""
    return {
        "done": state.done,
        "total": state.total,
        "units": [(c.kind.value, c.done, c.total) for c in state.units],
        "unit": state.unit and (state.unit.kind.value, state.unit.genius_id, state.unit.name),
        "items": [(c.kind.value, c.done, c.total) for c in state.items],
        "active": state.active and (state.active.kind.value, state.active.genius_id),
    }


async def import_all(
    sessionmaker: async_sessionmaker[AsyncSession],
    fake: FakeGenius,
    task: Task,
    progress: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Run the importer like a job does (without the job); returns the failures of non-root tasks."""

    async def record_progress(state: Progress) -> None:
        if progress is not None:
            progress.append(snapshot(state))

    return await run_tasks(sessionmaker, Context(fake), task, record_progress)  # type: ignore[arg-type]
