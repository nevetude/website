import asyncio
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind, ImportState
from music_backend.imports.client import GeniusError, RateLimitedError, RequestLog
from music_backend.imports.common import Context, Task
from music_backend.imports.runner import WORKERS
from music_backend.models import Album, Artist, Genre, Song, Tag
from tests.fakes import FakeGenius, album_payload, import_all, person, song_payload, track

type SessionMaker = async_sessionmaker[AsyncSession]


async def test_an_artist_met_many_times_is_fetched_once(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        albums={100: album_payload(100, primary_artists=[person(77)])},
        tracks={100: [track(500), track(501)]},
        songs={
            500: song_payload(500, primary_artists=[person(77)]),
            501: song_payload(501, primary_artists=[person(77)]),
        },
    )

    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    assert fake.calls.count("/artists/77") == 1
    assert fake.calls.count("/songs/500") == fake.calls.count("/songs/501") == 1


async def test_each_album_is_finished_before_the_next_one_starts(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        discographies={1: [10, 20]},
        tracks={10: [track(101)], 20: [track(201)]},
    )

    await import_all(sessionmaker, fake, Task(ImportKind.DISCOGRAPHY, 1))

    # stopping here would leave album 10 complete, not half of every album
    assert fake.calls.index("/songs/101") < fake.calls.index("/albums/20")
    assert fake.calls[:3] == ["/artists/1", "/artists/1/albums", "/albums/10"]


async def test_a_failing_entity_is_reported_and_the_rest_continues(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(tracks={100: [track(500), track(501), track(502)]}, missing={"/songs/501"})

    failures = await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    assert failures == ["song 501: Genius answered 404 for /songs/501"]
    async with sessionmaker() as db:
        states = {s.genius_id: s.import_state for s in await db.scalars(select(Song))}
    assert states == {500: ImportState.FULL, 501: ImportState.STUB, 502: ImportState.FULL}


async def test_a_failing_root_raises(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(missing={"/songs/1"})

    with pytest.raises(GeniusError):
        await import_all(sessionmaker, fake, Task(ImportKind.SONG, 1))


async def test_one_entity_is_one_transaction(sessionmaker: SessionMaker) -> None:
    broken = song_payload(
        501,
        primary_artists=[person(55, "Half Saved")],
        primary_tag={"id": 98, "name": "Odd"},
        tags=[
            {"id": 98, "name": "Odd"},
            {"id": 99},
        ],  # the second tag has no name: fails after the writes above
    )
    fake = FakeGenius(tracks={100: [track(500), track(501)]}, songs={501: broken})

    failures = await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    assert len(failures) == 1
    async with sessionmaker() as db:
        assert (
            await db.scalar(select(Album.import_state).where(Album.genius_id == 100))
        ) == ImportState.FULL
        assert (
            await db.scalar(select(Song.import_state).where(Song.genius_id == 500))
        ) == ImportState.FULL
        # the broken song kept nothing of its half-done work
        assert (
            await db.scalar(select(Song.import_state).where(Song.genius_id == 501))
        ) == ImportState.STUB
        assert await db.scalar(select(Tag).where(Tag.genius_id == 98)) is None
        assert await db.scalar(select(Genre).where(Genre.genius_id == 98)) is None
        assert await db.scalar(select(Artist).where(Artist.genius_id == 55)) is None


async def test_progress_totals_are_known_early_and_never_grow(sessionmaker: SessionMaker) -> None:
    progress: list[dict[str, Any]] = []
    fake = FakeGenius(
        discographies={1: [10, 20]},
        albums={10: album_payload(10, primary_artists=[person(5)])},
        tracks={10: [track(101), track(102)], 20: [track(201)]},
        songs={101: song_payload(101, primary_artists=[person(7)], featured_artists=[person(8)])},
    )

    await import_all(sessionmaker, fake, Task(ImportKind.DISCOGRAPHY, 1), progress)

    # the root reads the artist and lists the albums; after that the albums are the units
    assert progress[0]["total"] is None
    after_listing = progress[1]
    assert after_listing["units"] == [("album", 0, 2)]
    for step in progress[1:]:
        assert [(k, t) for k, _, t in step["units"]] == [("album", 2)]
    # while album 10 is imported its own items are fixed too, however many artists its songs bring
    inside_first_album = [p for p in progress if p["unit"] == ("album", 10, "Album 10")]
    assert {tuple(p["items"]) for p in inside_first_album if p["items"]} >= {
        (("artist", 0, 1), ("song", 0, 2)),
        (("artist", 1, 1), ("song", 2, 2)),
    }
    assert [(k, t) for k, _, t in inside_first_album[-1]["items"]] == [("artist", 1), ("song", 2)]
    last = progress[-1]
    assert (last["done"], last["total"], last["active"], last["unit"]) == (2, 2, None, None)


async def test_a_429_anywhere_stops_the_whole_import(sessionmaker: SessionMaker) -> None:
    class Limited(FakeGenius):
        async def get(self, path: str, params: Any = None, record: Any = None) -> Any:
            if path == "/songs/501":
                raise RateLimitedError("Genius answered 429", 429)
            return await super().get(path, params, record)

    fake = Limited(tracks={100: [track(500 + n) for n in range(8)]})

    with pytest.raises(RateLimitedError):
        await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    assert "/songs/507" not in fake.calls  # not skipped like a failed entity: nothing goes on


async def test_a_request_is_tagged_with_the_most_specific_task() -> None:
    tags: list[tuple[ImportKind | None, int | None]] = []

    class Client:
        async def get(self, path: str, params: Any, record: Any) -> dict[str, Any]:
            await record(RequestLog(path, 200, 1, 1, 1))
            return {}

    async def record(entry: RequestLog) -> None:
        tags.append((entry.task_kind, entry.task_genius_id))

    outer = Context(Client(), record).for_task(Task(ImportKind.DISCOGRAPHY, 1))  # type: ignore[arg-type]

    await outer.get("/artists/1/albums")  # the listing belongs to the discography task
    await outer.for_task(Task(ImportKind.ARTIST, 1)).get("/artists/1")  # the artist to its own

    assert tags == [(ImportKind.DISCOGRAPHY, 1), (ImportKind.ARTIST, 1)]


class Slow(FakeGenius):
    """Every answer takes a moment, so handlers really overlap; `peak` is the most requests in flight."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.in_flight = self.peak = 0

    async def get(self, path: str, params: Any = None, record: Any = None) -> Any:
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        await asyncio.sleep(0.05)
        try:
            return await super().get(path, params, record)
        finally:
            self.in_flight -= 1


async def test_the_items_of_an_album_run_in_parallel_up_to_the_workers(
    sessionmaker: SessionMaker,
) -> None:
    fake = Slow(discographies={1: [100]}, tracks={100: [track(500 + n) for n in range(9)]})

    failures = await import_all(sessionmaker, fake, Task(ImportKind.DISCOGRAPHY, 1))

    assert (fake.peak, failures) == (WORKERS, [])


async def test_parallel_songs_that_share_new_rows_do_not_fail(sessionmaker: SessionMaker) -> None:
    # The same new artist, tag and credit role in every song: the rows are created by whoever is first.
    songs = {
        500 + n: song_payload(500 + n, writer_artists=[person(88)], featured_artists=[person(89)])
        for n in range(6)
    }
    fake = Slow(discographies={1: [100]}, tracks={100: [track(n) for n in songs]}, songs=songs)

    failures = await import_all(sessionmaker, fake, Task(ImportKind.DISCOGRAPHY, 1))

    assert failures == []
    async with sessionmaker() as db:
        full = await db.scalars(select(Song.genius_id).where(Song.import_state == ImportState.FULL))
        assert set(full) == set(songs)
