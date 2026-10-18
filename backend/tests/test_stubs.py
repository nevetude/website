"""A stub is an entity Genius only mentioned in a list: what the list did not say must stay NULL."""

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ImportKind, ImportState
from music_backend.imports.common import Follow, Task
from music_backend.models import Album, AlbumTrack, Artist, Song
from music_backend.models.base import GeniusEntity
from tests.fakes import (
    FakeGenius,
    album_payload,
    artist_payload,
    import_all,
    person,
    related_album,
    song_payload,
    track,
)

type SessionMaker = async_sessionmaker[AsyncSession]

# What a list entry carries, per model. artist_type is also set when somebody lists the stub as a group.
KNOWN_FROM_A_LIST: dict[type[GeniusEntity], set[str]] = {
    Artist: {"name", "base_name", "cover_url", "artist_type"},
    Album: {"name", "base_name", "cover_url"},
    Song: {"name", "base_name"},
}
ALWAYS_SET = {"id", "genius_id", "import_state", "created_at", "updated_at"}


async def test_a_stub_knows_only_what_the_list_said(sessionmaker: SessionMaker) -> None:
    fake = FakeGenius(
        artists={
            1: artist_payload(1, members=(person(2),), groups=(person(3),)),
            # the group of an artist is imported in full with its members; the groups of those are stubs
            3: artist_payload(3, members=(person(1), person(4))),
            4: artist_payload(4, groups=(person(50),)),
        },
        albums={
            100: album_payload(
                100,
                primary_artists=[person(1)],
                performance_groups=[{"label": "Label", "artists": [person(10)]}],
                album_relationships=[
                    {"relationship_type": "deluxe_edition_of", "albums": [related_album(200)]}
                ],
            )
        },
        tracks={100: [track(500), track(501, disc=None, number=None)]},
        songs={
            500: song_payload(
                500,
                featured_artists=[person(5)],
                album=related_album(300),
                albums=[related_album(300)],
                song_relationships=[
                    {"relationship_type": "samples", "songs": [{"id": 700, "title": "Sampled"}]}
                ],
            )
        },
    )
    await import_all(sessionmaker, fake, Task(ImportKind.ALBUM, 100, follow=Follow.NONE))
    await import_all(sessionmaker, fake, Task(ImportKind.ARTIST, 1, follow=Follow.NONE))

    async with sessionmaker() as db:
        for model, known in KNOWN_FROM_A_LIST.items():
            columns = list(inspect(model, raiseerr=True).local_table.columns)
            rows = (
                await db.execute(select(*columns).where(model.import_state == ImportState.STUB))
            ).all()
            assert rows, f"no {model.__name__} stubs: the test would prove nothing"
            for row in rows:
                filled = {name for name, value in row._mapping.items() if value is not None}
                assert filled <= known | ALWAYS_SET, (model.__name__, row._mapping)

        # a stub nobody called a group has no type; one listed as a group is known to be one
        type_rows = await db.execute(select(Artist.genius_id, Artist.artist_type))
        types = dict(type_rows.all())
        assert (types[2], types[50]) == (None, "group")

        # the album import knows the numbers but not the primary album; the song import the reverse
        placements = {
            (album, song): (disc, position, sort_order, is_primary)
            for album, song, disc, position, sort_order, is_primary in await db.execute(
                select(
                    Album.genius_id,
                    Song.genius_id,
                    AlbumTrack.disc_number,
                    AlbumTrack.position,
                    AlbumTrack.sort_order,
                    AlbumTrack.is_primary,
                )
                .join(AlbumTrack, AlbumTrack.album_id == Album.id)
                .join(Song, Song.id == AlbumTrack.song_id)
            )
        }
    assert placements == {
        (100, 500): (1, 1, 1, None),
        (100, 501): (None, None, 2, None),
        (300, 500): (None, None, None, True),
    }
