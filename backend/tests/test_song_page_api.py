from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import SongArtistRole, SongRelationType
from music_backend.models import (
    CreditRole,
    GeniusResponse,
    Genre,
    SongArtist,
    SongAudio,
    SongCredit,
    SongRelationship,
    SongTag,
    SongVideo,
    Tag,
)
from tests.factories import make_album, make_artist, make_song, place

type SessionMaker = async_sessionmaker[AsyncSession]


async def arrange(sessionmaker: SessionMaker) -> dict[str, int]:
    """A song with a guest and a producer, on two albums, a remix of it, and a clip."""
    async with sessionmaker() as db:
        main = await make_artist(db, "Main", genius_id=1)
        guest = await make_artist(db, "Guest", genius_id=2)
        producer = await make_artist(db, "Producer", genius_id=3)
        producer_role = CreditRole(name="Producer")
        rock = Genre(name="Rock", base_name="Rock")
        tag = Tag(name="Guitar", base_name="Guitar")
        db.add_all([producer_role, rock, tag])
        await db.flush()
        song = await make_song(
            db, "Opener", genius_id=50, genre_id=rock.id, view_count=900, description="About it"
        )
        remix = await make_song(db, "Opener (Remix)", genius_id=51, variant="Remix")
        record = await make_album(db, "Record", genius_id=100)
        single = await make_album(db, "Single", genius_id=101)
        await place(db, record, song, position=1, disc_number=1)
        await place(db, single, song, position=1, is_primary=True)
        db.add_all(
            [
                SongArtist(song_id=song.id, artist_id=main.id, role=SongArtistRole.PRIMARY),
                SongArtist(song_id=song.id, artist_id=guest.id, role=SongArtistRole.FEATURED),
                SongArtist(song_id=remix.id, artist_id=guest.id, role=SongArtistRole.PRIMARY),
                SongCredit(song_id=song.id, artist_id=producer.id, role_id=producer_role.id),
                SongTag(song_id=song.id, tag_id=tag.id),
                SongRelationship(
                    song_id=remix.id, related_song_id=song.id, type=SongRelationType.REMIX_OF
                ),
                SongVideo(song_id=song.id, url="https://youtu.be/abc", start_seconds=5),
                SongAudio(song_id=song.id, provider="spotify", url="https://spotify/x"),
                GeniusResponse(
                    entity_type="song",
                    entity_id=song.id,
                    raw={
                        "title": "Opener",
                        "description": {"dom": {"tag": "root", "children": []}},
                    },
                ),
            ]
        )
        await db.commit()
        return {"song": song.id, "remix": remix.id}


async def test_the_song_with_everything_around_it(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    song = (await api.get(f"/api/v1/songs/{ids['song']}")).json()

    assert (song["base_name"], song["genre"], song["tags"], song["view_count"]) == (
        "Opener",
        "Rock",
        ["Guitar"],
        900,
    )
    assert [a["base_name"] for a in song["artists"]] == ["Main"]
    assert [a["base_name"] for a in song["featured"]] == ["Guest"]
    assert [(g["role"], [a["base_name"] for a in g["artists"]]) for g in song["credits"]] == [
        ("Producer", ["Producer"])
    ]
    # The primary album first, then the others.
    assert [(p["album"]["base_name"], p["is_primary"], p["position"]) for p in song["albums"]] == [
        ("Single", True, 1),
        ("Record", None, 1),
    ]
    assert song["description_dom"]["tag"] == "root"
    assert [(v["url"], v["start_seconds"]) for v in song["videos"]] == [("https://youtu.be/abc", 5)]
    assert [(a["provider"], a["url"]) for a in song["audios"]] == [("spotify", "https://spotify/x")]


async def test_a_relation_is_seen_from_both_sides(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    original = (await api.get(f"/api/v1/songs/{ids['song']}")).json()["related"]
    remix = (await api.get(f"/api/v1/songs/{ids['remix']}")).json()["related"]

    assert [(r["type"], r["inverse"], [s["base_name"] for s in r["songs"]]) for r in original] == [
        ("remix_of", True, ["Opener (Remix)"])
    ]
    assert original[0]["songs"][0]["artists"] == ["Guest"]
    assert [(r["type"], r["inverse"], [s["base_name"] for s in r["songs"]]) for r in remix] == [
        ("remix_of", False, ["Opener"])
    ]


async def test_the_raw_response_and_an_unknown_song(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    raw = (await api.get(f"/api/v1/songs/{ids['song']}/raw")).json()
    assert raw["title"] == "Opener"
    assert (await api.get(f"/api/v1/songs/{ids['remix']}/raw")).json() is None  # a stub has none
    assert (await api.get("/api/v1/songs/999999")).status_code == 404
