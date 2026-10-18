from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ArtistType, ImportKind, ImportState, JobStatus, SongArtistRole
from music_backend.models import CreditRole, ImportJob, SongArtist, SongCredit
from tests.factories import make_artist, make_song

type SessionMaker = async_sessionmaker[AsyncSession]


async def names(api: AsyncClient, query: str = "") -> list[str]:
    response = await api.get(f"/api/v1/artists?{query}")
    assert response.status_code == 200
    return [item["base_name"] for item in response.json()["items"]]


async def test_filters_pick_the_blocks_of_the_home_page(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        await make_artist(db, "Imported", genius_id=1, artist_type=ArtistType.PERSON)
        await make_artist(db, "Band", genius_id=2, artist_type=ArtistType.GROUP)
        await make_artist(db, "Solo", genius_id=3, artist_type=ArtistType.PERSON)
        await make_artist(
            db,
            "Stub Band",
            genius_id=4,
            artist_type=ArtistType.GROUP,
            import_state=ImportState.STUB,
        )
        await make_artist(db, "Stub Solo", genius_id=5, import_state=ImportState.STUB)
        db.add_all(
            [
                # only a finished import of the whole discography counts
                ImportJob(kind=ImportKind.DISCOGRAPHY, genius_id=1, status=JobStatus.SUCCEEDED),
                ImportJob(kind=ImportKind.DISCOGRAPHY, genius_id=3, status=JobStatus.FAILED),
                ImportJob(kind=ImportKind.ARTIST, genius_id=2, status=JobStatus.SUCCEEDED),
            ]
        )
        await db.commit()

    full = "import_state=full"
    assert await names(api, f"{full}&discography_imported=true") == ["Imported"]
    assert await names(api, f"{full}&discography_imported=false&is_group=true") == ["Band"]
    assert await names(api, f"{full}&discography_imported=false&is_group=false") == ["Solo"]
    assert await names(api, "import_state=stub&is_group=true") == ["Stub Band"]
    assert await names(api, "import_state=stub&is_group=false") == ["Stub Solo"]  # NULL type counts


async def test_sorting_by_name_followers_and_tracks(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        a = await make_artist(db, "alpha", followers_count=10)
        await make_artist(db, "Beta", followers_count=500)
        c = await make_artist(db, "Gamma")  # followers unknown
        songs = [await make_song(db, f"s{i}") for i in range(3)]
        for song in songs:  # Gamma has three tracks, Alpha one (as a featured artist), Beta none
            db.add(SongArtist(song_id=song.id, artist_id=c.id, role=SongArtistRole.PRIMARY))
        db.add(SongArtist(song_id=songs[0].id, artist_id=a.id, role=SongArtistRole.FEATURED))
        await db.commit()

    assert await names(api) == ["alpha", "Beta", "Gamma"]  # case-insensitive
    assert await names(api, "order=desc") == ["Gamma", "Beta", "alpha"]
    assert await names(api, "sort=followers") == ["Beta", "alpha", "Gamma"]  # unknown goes last
    assert await names(api, "sort=followers&order=asc") == ["alpha", "Beta", "Gamma"]
    tracks = (await api.get("/api/v1/artists?sort=tracks")).json()["items"]
    assert [(i["base_name"], i["tracks_count"]) for i in tracks] == [
        ("Gamma", 3),
        ("alpha", 1),
        ("Beta", 0),
    ]


async def test_roles_are_combined_with_and_and_counted(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        both = await make_artist(db, "Both")
        producer = await make_artist(db, "Producer only")
        await make_artist(db, "Nothing")
        song = await make_song(db, "Song")
        role = CreditRole(name="Producer")
        db.add(role)
        await db.flush()
        db.add_all(
            [
                SongArtist(song_id=song.id, artist_id=both.id, role=SongArtistRole.PRIMARY),
                SongCredit(song_id=song.id, artist_id=both.id, role_id=role.id),
                SongCredit(song_id=song.id, artist_id=producer.id, role_id=role.id),
            ]
        )
        await db.commit()

    assert await names(api, "roles=Producer") == ["Both", "Producer only"]
    assert await names(api, "roles=Producer&roles=Artist") == ["Both"]  # in both groups at once
    assert await names(api, "roles=Producer&roles=Featured") == []
    page = (await api.get("/api/v1/artists?roles=Producer&limit=1")).json()
    assert (page["total"], len(page["items"])) == (2, 1)
    counts = (await api.get("/api/v1/artists/roles")).json()
    assert counts == [{"role": "Producer", "artists": 2}, {"role": "Artist", "artists": 1}]


async def test_an_artist_row_carries_what_the_card_shows(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        await make_artist(
            db,
            "Radiohead",
            genius_id=604,
            genius_url="https://genius.com/artists/Radiohead",
            cover_url="https://img/r.jpg",
            is_verified=True,
            followers_count=1234,
        )
        await db.commit()

    (card,) = (await api.get("/api/v1/artists")).json()["items"]

    assert card | {"id": 0} == {
        "id": 0,
        "genius_id": 604,
        "base_name": "Radiohead",
        "cover_url": "https://img/r.jpg",
        "genius_url": "https://genius.com/artists/Radiohead",
        "is_verified": True,
        "followers_count": 1234,
        "tracks_count": 0,
        "artist_type": None,
        "import_state": "full",
    }
