from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import (
    DatePrecision,
    ImportKind,
    ImportState,
    SongArtistRole,
    SongRelationType,
)
from music_backend.imports.common import Follow, Task
from music_backend.models import (
    Album,
    AlbumTrack,
    Artist,
    CreditRole,
    Genre,
    Song,
    SongArtist,
    SongAudio,
    SongCredit,
    SongRelationship,
    SongTag,
    SongVideo,
    Tag,
)
from tests.fakes import (
    FakeGenius,
    album_payload,
    artist_payload,
    description,
    import_all,
    person,
    related_album,
    song_payload,
    track,
)

type SessionMaker = async_sessionmaker[AsyncSession]


def rich_song(**overrides: object) -> dict[str, object]:
    """A song with every field the importer reads filled in."""
    return (
        song_payload(
            28,
            "Надоела (Freestyle) (Tired of you)",
            language="ru",
            release_date_components={"year": 1993, "month": None, "day": None},
            description=description("The meaning of the song."),
            recording_location="Firehouse Studio",
            explicit=True,
            stats={"pageviews": 2537502},
            primary_tag={"id": 1434, "name": "Rap"},
            tags=[{"id": 1434, "name": "Rap"}, {"id": 886, "name": "Русский (In Russian)"}],
            primary_artists=[person(1, "Main")],
            featured_artists=[person(2, "Guest")],
            writer_artists=[person(3, "Writer One")],
            producer_artists=[person(4, "Producer One")],
            custom_performances=[
                {"label": "Label", "artists": [person(5, "Some Records")]},
                {"label": "Mixing Engineer", "artists": [person(3, "Writer One")]},
            ],
            song_relationships=[
                {"relationship_type": "samples", "songs": [{"id": 700, "title": "Source"}]},
                {"relationship_type": "remixed_by", "songs": [{"id": 701, "title": "A Remix"}]},
                {"relationship_type": "cover_of", "songs": []},
            ],
            media=[
                {
                    "provider": "youtube",
                    "type": "video",
                    "url": "https://youtube.com/x",
                    "start": 0,
                },
                {
                    "provider": "spotify",
                    "type": "audio",
                    "url": "https://open.spotify.com/track/1",
                    "native_uri": "spotify:track:1",
                    "attribution": "Spotify",
                },
            ],
            album=related_album(10, "Album A"),
            albums=[related_album(10, "Album A"), related_album(11, "Album B")],
        )
        | overrides
    )


async def one_song(sm: SessionMaker, genius_id: int = 28) -> Song:
    async with sm() as db:
        song = await db.scalar(select(Song).where(Song.genius_id == genius_id))
    assert song is not None
    return song


async def test_song_stores_every_chosen_field(sessionmaker: SessionMaker) -> None:
    await import_all(sessionmaker, FakeGenius(songs={28: rich_song()}), Task(ImportKind.SONG, 28))

    song = await one_song(sessionmaker)
    assert (song.name, song.base_name, song.variant, song.disambiguator) == (
        "Надоела (Freestyle) (Tired of you)",
        "Надоела",
        "Freestyle",
        "Tired of you",
    )
    assert (song.language, song.import_state) == ("ru", ImportState.FULL)
    assert (song.release_date, song.release_date_precision) == (
        date(1993, 1, 1),
        DatePrecision.YEAR,
    )
    assert (song.description, song.recording_location) == (
        "The meaning of the song.",
        "Firehouse Studio",
    )
    assert (song.explicit, song.instrumental, song.is_music, song.hidden, song.published) == (
        True,
        False,
        True,
        False,
        True,
    )
    assert (song.lyrics_state, song.genius_url, song.view_count) == (
        "complete",
        "https://genius.com/songs/28",
        2537502,
    )
    assert (song.cover_url, song.cover_thumbnail_url) == (
        "https://img/art.jpg",
        "https://img/art-thumb.jpg",
    )
    assert (song.cover_primary_color, song.cover_secondary_color) == ("#111111", "#222222")


async def test_song_artists_credits_tags_genre_links_and_relations(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(sessionmaker, FakeGenius(songs={28: rich_song()}), Task(ImportKind.SONG, 28))

    async with sessionmaker() as db:
        song = await one_song(sessionmaker)
        by_role = (
            await db.execute(
                select(SongArtist.role, Artist.name)
                .join(Artist, Artist.id == SongArtist.artist_id)
                .order_by(SongArtist.role, SongArtist.position)
            )
        ).all()
        assert [tuple(r) for r in by_role] == [
            (SongArtistRole.FEATURED, "Guest"),
            (SongArtistRole.PRIMARY, "Main"),
        ]

        credit_rows = (
            await db.execute(
                select(CreditRole.name, Artist.name, SongCredit.label_text)
                .join(SongCredit, SongCredit.role_id == CreditRole.id)
                .join(Artist, Artist.id == SongCredit.artist_id)
                .order_by(CreditRole.name, Artist.name)
            )
        ).all()
        assert [tuple(c) for c in credit_rows] == [
            ("Label", "Some Records", "Label"),
            ("Mixing Engineer", "Writer One", "Mixing Engineer"),
            ("Producer", "Producer One", "Producer"),
            ("Writer", "Writer One", "Writer"),  # one artist, two roles
        ]

        genre = await db.get_one(Genre, song.genre_id)
        assert (genre.genius_id, genre.name) == (1434, "Rap")
        tags = (
            await db.execute(
                select(Tag.name, Tag.base_name, Tag.disambiguator)
                .join(SongTag, SongTag.tag_id == Tag.id)
                .order_by(Tag.genius_id)
            )
        ).all()
        assert [tuple(t) for t in tags] == [
            ("Русский (In Russian)", "Русский", "In Russian"),
            ("Rap", "Rap", None),
        ]

        genius = {s.id: s.genius_id for s in await db.scalars(select(Song))}
        relations = (
            await db.execute(
                select(
                    SongRelationship.song_id,
                    SongRelationship.related_song_id,
                    SongRelationship.type,
                )
            )
        ).all()
        assert sorted((genius[a], genius[b], t) for a, b, t in relations) == sorted(
            [
                (28, 700, SongRelationType.SAMPLES),
                (
                    701,
                    28,
                    SongRelationType.REMIX_OF,
                ),  # "remixed_by" is stored from the remix's side
            ]
        )
        songs = {x.genius_id: x.import_state for x in await db.scalars(select(Song))}
        assert songs[700] == ImportState.STUB

        links = (
            await db.execute(
                select(
                    SongAudio.provider,
                    SongAudio.native_uri,
                    SongAudio.attribution,
                ).order_by(SongAudio.provider)
            )
        ).all()
        assert [tuple(link) for link in links] == [("spotify", "spotify:track:1", "Spotify")]
        videos = (
            await db.execute(
                select(SongVideo.start_seconds, SongVideo.explicit, SongVideo.official)
            )
        ).all()
        # the video is in its own table; `explicit` and `official` are false until somebody sets them
        assert [tuple(video) for video in videos] == [(0, False, False)]


async def test_every_artist_found_is_imported_in_full(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(songs={28: rich_song()})

    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 28))

    async with sessionmaker() as db:
        states = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
    assert states == dict.fromkeys(range(1, 6), ImportState.FULL)
    assert "/songs/700" not in fake.calls  # related songs stay stubs


async def test_placements_are_created_without_a_position_and_the_primary_album_is_marked(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(sessionmaker, FakeGenius(songs={28: rich_song()}), Task(ImportKind.SONG, 28))

    async with sessionmaker() as db:
        rows = (
            await db.execute(
                select(
                    Album.genius_id, Album.import_state, AlbumTrack.position, AlbumTrack.is_primary
                )
                .join(AlbumTrack, AlbumTrack.album_id == Album.id)
                .order_by(Album.genius_id)
            )
        ).all()
    assert [tuple(r) for r in rows] == [
        (10, ImportState.STUB, None, True),
        (11, ImportState.STUB, None, False),
    ]


async def test_the_albums_import_fills_in_the_position_the_song_import_left_empty(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        songs={28: rich_song()},
        albums={10: album_payload(10, "Album A")},
        tracks={10: [track(28, "Надоела", 1, 7)]},
    )
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 28))

    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 10, follow=Follow.NONE))

    async with sessionmaker() as db:
        placements = (
            await db.scalars(
                select(AlbumTrack)
                .join(Album, Album.id == AlbumTrack.album_id)
                .where(Album.genius_id == 10)
            )
        ).all()
    assert [(p.position, p.is_primary) for p in placements] == [
        (7, True)
    ]  # one placement, now numbered


async def test_a_single_without_an_album_has_no_placements(sessionmaker: SessionMaker) -> None:
    await import_all(
        sessionmaker,
        FakeGenius(songs={5: song_payload(5, album=None, albums=[])}),
        Task(ImportKind.SONG, 5),
    )

    async with sessionmaker() as db:
        assert (await db.scalars(select(AlbumTrack))).all() == []


async def test_tags_and_genres_are_shared_between_songs(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(songs={1: song_payload(1), 2: song_payload(2)})
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 1))

    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 2))

    async with sessionmaker() as db:
        assert len((await db.scalars(select(Tag))).all()) == 1
        assert len((await db.scalars(select(Genre))).all()) == 1
        assert len((await db.scalars(select(SongTag))).all()) == 2


async def test_importing_an_unchanged_song_again_writes_nothing(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(songs={28: rich_song()})
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 28))

    async def snapshot() -> tuple[object, ...]:
        async with sessionmaker() as db:
            tables = (
                Song,
                Artist,
                Album,
                AlbumTrack,
                SongArtist,
                SongCredit,
                SongTag,
                SongAudio,
                SongVideo,
                SongRelationship,
                CreditRole,
                Tag,
                Genre,
            )
            counts = [len((await db.scalars(select(t))).all()) for t in tables]
            stamps = [(await db.scalars(select(t.updated_at))).all() for t in (Song, Artist, Album)]
            return (*counts, *stamps)

    before = await snapshot()
    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 28))

    assert await snapshot() == before


async def test_a_song_without_a_view_count_is_imported(sessionmaker: SessionMaker) -> None:
    payload = song_payload(
        5, stats={"contributors": 1}
    )  # Genius leaves pageviews out for most songs

    await import_all(sessionmaker, FakeGenius(songs={5: payload}), Task(ImportKind.SONG, 5))

    assert (await one_song(sessionmaker, 5)).view_count is None


async def test_a_song_without_any_release_date_is_imported(sessionmaker: SessionMaker) -> None:
    # Real case (song 8902271): release_date_components is null, not {"year": null, ...}
    payload = song_payload(5, release_date_components=None)

    await import_all(sessionmaker, FakeGenius(songs={5: payload}), Task(ImportKind.SONG, 5))

    song = await one_song(sessionmaker, 5)
    assert (song.import_state, song.release_date, song.release_date_precision) == (
        ImportState.FULL,
        None,
        None,
    )


async def test_a_song_stub_does_not_pretend_to_know_the_flags(sessionmaker: SessionMaker) -> None:
    await import_all(sessionmaker, FakeGenius(songs={28: rich_song()}), Task(ImportKind.SONG, 28))

    stub = await one_song(sessionmaker, 700)  # a related song: known only by its id and title
    assert stub.import_state == ImportState.STUB
    assert (stub.explicit, stub.instrumental, stub.is_music, stub.hidden, stub.published) == (
        None,
    ) * 5


async def test_an_artist_of_a_song_brings_its_groups_with_all_their_members(
    sessionmaker: SessionMaker,
) -> None:
    fake = FakeGenius(
        songs={1: song_payload(1, primary_artists=[person(10, "Thom")])},
        artists={
            10: artist_payload(10, "Thom", groups=(person(20, "Atoms for Peace"),)),
            20: artist_payload(20, "Atoms for Peace", members=(person(10), person(30, "Flea"))),
            30: artist_payload(30, "Flea", groups=(person(40, "Red Hot"),)),
        },
    )

    await import_all(sessionmaker, fake, Task(ImportKind.SONG, 1))

    async with sessionmaker() as db:
        states = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
    # the group and all its members in full; the other group of a member only as a stub
    full, stub = ImportState.FULL, ImportState.STUB
    assert states == {10: full, 20: full, 30: full, 40: stub}
