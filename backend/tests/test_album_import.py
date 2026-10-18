from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.api.queries import raw_of
from music_backend.enums import (
    AlbumRelationType,
    AlbumType,
    DatePrecision,
    ImportKind,
    ImportState,
)
from music_backend.imports.common import Follow, Task, partial_date
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
    Revision,
    Song,
)
from tests.fakes import (
    FakeGenius,
    album_payload,
    artist_payload,
    description,
    import_all,
    person,
    related_album,
    track,
)

type SessionMaker = async_sessionmaker[AsyncSession]

COVERS = [
    {
        "id": 9001,
        "image_url": "https://img/c1.jpg",
        "thumbnail_image_url": "https://img/t1.jpg",
        "url": "https://genius.com/cover/9001",
    },
    {
        "id": 9002,
        "image_url": "https://img/c2.jpg",
        "thumbnail_image_url": "https://img/t2.jpg",
        "url": "https://genius.com/cover/9002",
    },
]


def rich_album(**overrides: object) -> dict[str, object]:
    """An album with every field the importer reads filled in."""
    return (
        album_payload(
            100,
            "Надоела (Live) (Tired of you)",
            album_type="live",
            language="ru",
            release_date_components={"year": 2010, "month": None, "day": None},
            description_annotation={"annotations": [{"body": description("A live record.")}]},
            comment_count=2,
            contributors_count=56,
            pyongs_count=3,
            primary_artists=[person(1, "Main Artist"), person(2, "Guest Artist")],
            cover_arts=COVERS,
            performance_groups=[
                {"label": "Label", "artists": [person(10, "Some Records")]},
                {
                    "label": "Copyright ©",
                    "artists": [person(10, "Some Records"), person(11, "Publisher")],
                },
            ],
            album_relationships=[
                {
                    "relationship_type": "deluxe_edition_of",
                    "albums": [related_album(200, "Original")],
                },
                {"relationship_type": "deluxe_editions", "albums": [related_album(201, "Deluxe")]},
                {"relationship_type": "alternate_version_of", "albums": []},
                {
                    "relationship_type": "reissue_of",
                    "albums": [related_album(202, "First Pressing")],
                },
                {"relationship_type": "remixes", "albums": [related_album(203, "The Remixes")]},
            ],
        )
        | overrides
    )


TRACKS = {
    100: [
        track(500, "Intro", 1, 1),
        track(501, "Second (Remix)", 1, 2),
        track(502, "Loose", None, None),
    ]
}


def fake_with_rich_album() -> FakeGenius:
    albums = {
        200: album_payload(
            200,
            "Original",
            album_relationships=[
                {"relationship_type": "deluxe_editions", "albums": [related_album(999, "Too far")]}
            ],
        )
    }
    artists = {
        i: artist_payload(i, n)
        for i, n in (
            (1, "Main Artist"),
            (2, "Guest Artist"),
            (10, "Some Records"),
            (11, "Publisher"),
        )
    }
    return FakeGenius(albums={100: rich_album(), **albums}, artists=artists, tracks=TRACKS)


@pytest.mark.parametrize(
    ("components", "expected"),
    [
        ({"year": 2010, "month": None, "day": None}, (date(2010, 1, 1), DatePrecision.YEAR)),
        ({"year": 2010, "month": 3, "day": None}, (date(2010, 3, 1), DatePrecision.MONTH)),
        ({"year": 2010, "month": 3, "day": 5}, (date(2010, 3, 5), DatePrecision.DAY)),
        ({"year": None, "month": None, "day": None}, (None, None)),
        (None, (None, None)),  # no date at all: Genius sends null instead of a dict
    ],
)
def test_partial_date(
    components: dict[str, int | None], expected: tuple[date | None, DatePrecision | None]
) -> None:
    assert partial_date(components) == expected


async def test_album_stores_every_chosen_field_and_link(sessionmaker: SessionMaker) -> None:
    await import_all(sessionmaker, fake_with_rich_album(), Task(ImportKind.ALBUM, 100))

    async with sessionmaker() as db:
        album = await db.scalar(select(Album).where(Album.genius_id == 100))
        assert album is not None
        assert (album.genius_id, album.import_state) == (100, ImportState.FULL)
        assert (album.name, album.base_name, album.variant, album.disambiguator) == (
            "Надоела (Live) (Tired of you)",
            "Надоела",
            "Live",
            "Tired of you",
        )
        assert (album.album_type, album.language) == (AlbumType.LIVE, "ru")
        assert (album.release_date, album.release_date_precision) == (
            date(2010, 1, 1),
            DatePrecision.YEAR,
        )
        assert album.description == "A live record."
        assert album.genius_url == "https://genius.com/albums/100"
        assert (album.cover_url, album.cover_thumbnail_url) == (
            "https://img/cover.jpg",
            "https://img/thumb.jpg",
        )
        assert (album.cover_primary_color, album.cover_secondary_color) == ("#111111", "#222222")

        names = (
            await db.scalars(
                select(Artist.name)
                .join(AlbumArtist, AlbumArtist.artist_id == Artist.id)
                .where(AlbumArtist.album_id == album.id)
                .order_by(AlbumArtist.position)
            )
        ).all()
        assert names == [
            "Main Artist",
            "Guest Artist",
        ]  # main artists come from primary_artists[] only

        covers = (await db.scalars(select(AlbumCoverArt).order_by(AlbumCoverArt.position))).all()
        assert [(c.genius_id, c.position, c.image_url) for c in covers] == [
            (9001, 1, "https://img/c1.jpg"),
            (9002, 2, "https://img/c2.jpg"),
        ]

        credit_rows = (
            await db.execute(
                select(CreditRole.name, Artist.name)
                .join(AlbumCredit, AlbumCredit.role_id == CreditRole.id)
                .join(Artist, Artist.id == AlbumCredit.artist_id)
                .order_by(CreditRole.name, Artist.name)
            )
        ).all()
        assert [tuple(c) for c in credit_rows] == [
            ("Copyright ©", "Publisher"),
            ("Copyright ©", "Some Records"),
            ("Label", "Some Records"),
        ]

        # each relation is stored once, in the "of" direction
        genius = {a.id: a.genius_id for a in await db.scalars(select(Album))}
        related = (
            await db.execute(
                select(
                    AlbumRelationship.album_id,
                    AlbumRelationship.related_album_id,
                    AlbumRelationship.type,
                )
            )
        ).all()
        assert sorted((genius[a], genius[b], t) for a, b, t in related) == sorted(
            [
                (100, 200, AlbumRelationType.DELUXE_EDITION_OF),
                (201, 100, AlbumRelationType.DELUXE_EDITION_OF),
                (100, 202, AlbumRelationType.REISSUE_OF),
                (203, 100, AlbumRelationType.REMIX_VERSION_OF),
                (
                    999,
                    200,
                    AlbumRelationType.DELUXE_EDITION_OF,
                ),  # from the related album's own import
            ]
        )

        # numbers Genius does not give stay empty
        rows = (
            await db.execute(
                select(
                    Song.genius_id,
                    AlbumTrack.disc_number,
                    AlbumTrack.position,
                    AlbumTrack.sort_order,
                )
                .join(AlbumTrack, AlbumTrack.song_id == Song.id)
                .where(AlbumTrack.album_id == album.id)
                .order_by(AlbumTrack.sort_order)
            )
        ).all()
        assert [tuple(r) for r in rows] == [(500, 1, 1, 1), (501, 1, 2, 2), (502, None, None, 3)]


async def test_what_an_album_brings_with_it(sessionmaker: SessionMaker) -> None:
    fake = fake_with_rich_album()

    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    async with sessionmaker() as db:
        state = {a.genius_id: a.import_state for a in await db.scalars(select(Album))}
        songs = {s.genius_id: s.import_state for s in await db.scalars(select(Song))}
        artists = {a.genius_id: a.import_state for a in await db.scalars(select(Artist))}
    full, stub = ImportState.FULL, ImportState.STUB
    # related albums are imported in full, but their own relations are only stubs
    assert state == {100: full, 200: full, 201: full, 202: full, 203: full, 999: stub}
    assert songs == {500: full, 501: full, 502: full}  # the songs of the tracklist
    # main artists and credit artists in full
    assert {i: artists[i] for i in (1, 2, 10, 11)} == {1: full, 2: full, 10: full, 11: full}
    assert "/albums/999" not in fake.calls


async def test_related_albums_are_not_followed_when_the_album_is_not_followed(
    sessionmaker: SessionMaker,
) -> None:
    fake = fake_with_rich_album()

    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100, follow=Follow.NONE))

    async with sessionmaker() as db:
        stubs = (
            await db.scalars(select(Album.genius_id).where(Album.import_state == ImportState.STUB))
        ).all()
    assert sorted(g for g in stubs if g) == [200, 201, 202, 203]
    assert not any(call.startswith("/albums/20") for call in fake.calls)


async def test_importing_an_unchanged_album_again_writes_nothing(
    sessionmaker: SessionMaker,
) -> None:
    fake = fake_with_rich_album()
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    async def snapshot() -> tuple[object, ...]:
        async with sessionmaker() as db:
            tables = (
                Album,
                Artist,
                Song,
                AlbumTrack,
                AlbumArtist,
                AlbumCredit,
                AlbumRelationship,
                AlbumCoverArt,
                Revision,
                CreditRole,
            )
            counts = [len((await db.scalars(select(t))).all()) for t in tables]
            stamps = [
                (await db.scalars(select(t.updated_at))).all()
                for t in (Album, Artist, Song, GeniusResponse)
            ]
            return (*counts, *stamps)

    before = await snapshot()
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100))

    assert await snapshot() == before


async def test_a_real_change_updates_the_album_and_refreshes_the_raw_copy(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(
        sessionmaker, fake_with_rich_album(), Task(ImportKind.ALBUM, 100, follow=Follow.NONE)
    )
    changed = FakeGenius(albums={100: rich_album(language="fr")}, tracks=TRACKS)

    await import_all(sessionmaker, changed, Task(ImportKind.ALBUM, 100, follow=Follow.NONE))

    async with sessionmaker() as db:
        album = await db.scalar(select(Album).where(Album.genius_id == 100))
        assert album is not None
        assert album.language == "fr"
        raw = await db.scalar(select(GeniusResponse.raw).where(raw_of("album", album.id)))
    assert raw is not None
    assert raw["language"] == "fr"


async def test_an_empty_description_becomes_null(sessionmaker: SessionMaker) -> None:
    empty = {"annotations": [{"body": description()}]}
    fake = FakeGenius(albums={100: rich_album(description_annotation=empty)}, tracks=TRACKS)

    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100, follow=Follow.NONE))

    async with sessionmaker() as db:
        album = await db.scalar(select(Album).where(Album.genius_id == 100))
    assert album is not None
    assert album.description is None


@pytest.mark.parametrize(
    ("name", "components", "expected"),
    [
        ("Out Now", {"year": 2020, "month": 5, "day": 17}, False),
        ("OFF THE STRENGTH*", {"year": 2026, "month": 1, "day": 1}, True),
        ("No Date Yet", {"year": None, "month": None, "day": None}, True),
        ("No Date At All", None, True),
    ],
)
async def test_unreleased_album_has_no_date_or_an_asterisk(
    sessionmaker: SessionMaker, name: str, components: dict[str, int | None] | None, expected: bool
) -> None:
    fake = FakeGenius()
    fake.albums[7] = album_payload(7, name, release_date_components=components)
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 7, follow=Follow.NONE))

    async with sessionmaker() as db:
        album = await db.scalar(select(Album).where(Album.genius_id == 7))
        assert album is not None
        assert album.is_released is not expected


@pytest.mark.parametrize("album_type", [t.value for t in AlbumType])
async def test_every_type_of_album_genius_knows_is_stored(
    sessionmaker: SessionMaker, album_type: str
) -> None:
    """A type missing from `AlbumType` fails the import of the album (soundtrack once did, album 681187)."""
    fake = FakeGenius()
    fake.albums[7] = album_payload(7, album_type=album_type)
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 7, follow=Follow.NONE))

    async with sessionmaker() as db:
        album = await db.scalar(select(Album).where(Album.genius_id == 7))
        assert album is not None
        assert album.album_type == album_type


async def test_explicit_is_false_at_import_and_survives_a_reimport(
    sessionmaker: SessionMaker,
) -> None:
    await import_all(sessionmaker, fake_with_rich_album(), Task(ImportKind.ALBUM, 100))
    async with sessionmaker() as db, db.begin():
        covers = (await db.scalars(select(AlbumCoverArt).order_by(AlbumCoverArt.position))).all()
        assert [c.explicit for c in covers] == [False, False]
        covers[0].explicit = True  # set by hand

    await import_all(sessionmaker, fake_with_rich_album(), Task(ImportKind.ALBUM, 100))

    async with sessionmaker() as db:
        covers = (await db.scalars(select(AlbumCoverArt).order_by(AlbumCoverArt.position))).all()
        assert [c.explicit for c in covers] == [True, False]
