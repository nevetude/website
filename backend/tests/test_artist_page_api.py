from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import ArtistType, ImportKind, JobStatus, SongArtistRole
from music_backend.models import (
    Album,
    AlbumArtist,
    AlbumCredit,
    ArtistAlias,
    ArtistMember,
    CreditRole,
    GeniusResponse,
    Genre,
    ImportJob,
    Song,
    SongArtist,
    SongAudio,
    SongCredit,
    SongVideo,
)
from tests.factories import make_album, make_artist, make_song, place

type SessionMaker = async_sessionmaker[AsyncSession]


async def arrange(sessionmaker: SessionMaker) -> dict[str, int]:
    """Thom is the main artist of one song, a producer of a second one, only a guest on a third."""
    async with sessionmaker() as db:
        thom = await make_artist(db, "Thom", genius_id=10)
        db.add(GeniusResponse(entity_type="artist", entity_id=thom.id, raw={"id": 10}))
        band = await make_artist(db, "Band", genius_id=11, artist_type=ArtistType.GROUP)
        flea = await make_artist(db, "Flea", genius_id=12)
        db.add_all(
            [
                ArtistAlias(artist_id=thom.id, name="T. Y."),
                ArtistMember(group_id=band.id, member_id=thom.id, position=1),
                ArtistMember(group_id=band.id, member_id=flea.id, position=2),
                ImportJob(kind=ImportKind.DISCOGRAPHY, genius_id=10, status=JobStatus.SUCCEEDED),
            ]
        )
        genre = Genre(name="Rock", base_name="Rock")
        db.add(genre)
        await db.flush()
        own = await make_song(db, "Own", genre_id=genre.id)
        produced = await make_song(db, "Produced", view_count=500)
        guest = await make_song(db, "Guest")
        producer = CreditRole(name="Producer")
        db.add(producer)
        await db.flush()
        db.add_all(
            [
                SongArtist(song_id=own.id, artist_id=thom.id, role=SongArtistRole.PRIMARY),
                SongCredit(song_id=own.id, artist_id=thom.id, role_id=producer.id),
                SongCredit(song_id=produced.id, artist_id=thom.id, role_id=producer.id),
                SongArtist(song_id=guest.id, artist_id=thom.id, role=SongArtistRole.FEATURED),
            ]
        )
        album = await make_album(db, "Album")
        await place(db, album, own, position=1, is_primary=True)
        db.add(AlbumArtist(album_id=album.id, artist_id=thom.id, position=1))
        remix = await make_album(db, "Remixes")
        db.add(AlbumCredit(album_id=remix.id, artist_id=thom.id, role_id=producer.id))
        label_role = CreditRole(name="Label")
        db.add(label_role)
        await db.flush()
        db.add(AlbumCredit(album_id=album.id, artist_id=band.id, role_id=label_role.id))
        await db.commit()
        return {"thom": thom.id, "band": band.id}


async def test_the_artist_with_everything_around_it(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    detail = (await api.get(f"/api/v1/artists/{ids['thom']}")).json()

    assert (detail["base_name"], detail["aliases"]) == ("Thom", ["T. Y."])
    assert [g["base_name"] for g in detail["groups"]] == ["Band"]
    assert (detail["songs_count"], detail["albums_count"]) == (3, 2)
    assert {r["role"]: r["works"] for r in detail["song_roles"]} == {
        "Artist": 1,
        "Producer": 2,
        "Featured": 1,
    }
    assert {r["role"]: r["works"] for r in detail["album_roles"]} == {"Artist": 1, "Producer": 1}
    assert detail["genres"] == [{"genre": "Rock", "songs": 1}]
    assert [(j["kind"], j["status"]) for j in detail["imports"]] == [("discography", "succeeded")]
    band = (await api.get(f"/api/v1/artists/{ids['band']}")).json()
    assert [m["base_name"] for m in band["members"]] == [
        "Thom",
        "Flea",
    ]  # in the order of the group


async def test_an_unknown_artist_is_a_404(api: AsyncClient) -> None:
    for tail in ("", "/songs", "/albums", "/raw"):
        assert (await api.get(f"/api/v1/artists/999{tail}")).status_code == 404


async def test_songs_by_role_with_all_the_roles_of_each(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    thom = (await arrange(sessionmaker))["thom"]

    everything = (await api.get(f"/api/v1/artists/{thom}/songs?sort=name")).json()
    assert [(s["base_name"], sorted(s["roles"])) for s in everything["items"]] == [
        ("Guest", ["Featured"]),
        ("Own", ["Artist", "Producer"]),
        ("Produced", ["Producer"]),
    ]
    both = (await api.get(f"/api/v1/artists/{thom}/songs?roles=Artist&roles=Producer")).json()
    assert [s["base_name"] for s in both["items"]] == ["Own"]  # the artist has both roles on it
    assert both["total"] == 1
    own = everything["items"][1]
    assert (own["genre"], own["album"]) == ("Rock", "Album")
    assert own["producers"] == [{"id": thom, "base_name": "Thom"}]
    assert everything["items"][0]["producers"] == []  # a song nobody is credited as its producer
    views = (await api.get(f"/api/v1/artists/{thom}/songs?sort=views")).json()["items"]
    assert views[0]["base_name"] == "Produced"  # no views goes last


async def test_albums_and_the_raw_response(api: AsyncClient, sessionmaker: SessionMaker) -> None:
    thom = (await arrange(sessionmaker))["thom"]

    albums = (await api.get(f"/api/v1/artists/{thom}/albums?sort=name")).json()
    assert [
        (a["base_name"], a["roles"], a["tracks_count"], a["artists"], a["labels"])
        for a in albums["items"]
    ] == [
        ("Album", ["Artist"], 1, ["Thom"], ["Band"]),  # the label is an artist credited as "Label"
        ("Remixes", ["Producer"], 0, [], []),
    ]
    only_credited = (await api.get(f"/api/v1/artists/{thom}/albums?roles=Producer")).json()
    assert [a["base_name"] for a in only_credited["items"]] == ["Remixes"]
    assert (await api.get(f"/api/v1/artists/{thom}/raw")).json() == {"id": 10}


async def test_unreleased_albums_are_shown_only_on_request(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    thom = (await arrange(sessionmaker))["thom"]
    async with sessionmaker() as db, db.begin():
        await db.execute(
            update(Album).where(Album.base_name == "Remixes").values(is_released=False)
        )

    hidden = (await api.get(f"/api/v1/artists/{thom}/albums")).json()
    assert [a["base_name"] for a in hidden["items"]] == ["Album"]
    assert hidden["total"] == 1
    shown = (await api.get(f"/api/v1/artists/{thom}/albums?include_unreleased=true")).json()
    assert sorted(a["base_name"] for a in shown["items"]) == ["Album", "Remixes"]
    assert shown["total"] == 2


async def test_real_name_dates_and_profile_links(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        rich = await make_artist(
            db,
            "Rich",
            description="Richard Roe (born June 17, 1987) is a rapper.",
        )
        # Genius sends "" for a missing link and bare handles for some networks.
        links = {"instagram": "rich", "spotify": "https://sp/rich", "tidal": ""}
        db.add(GeniusResponse(entity_type="artist", entity_id=rich.id, raw={"social_links": links}))
        plain = await make_artist(db, "Plain", description="Just a rapper.")
        await db.commit()

    detail = (await api.get(f"/api/v1/artists/{rich.id}")).json()
    assert detail["real_name"] == "Richard Roe"
    assert detail["born"] == {"date": "1987-06-17", "precision": "day"}
    assert detail["died"] is None
    assert detail["links"] == [
        {"kind": "spotify", "url": "https://sp/rich"},
        {"kind": "instagram", "url": "https://instagram.com/rich"},
    ]
    nothing = (await api.get(f"/api/v1/artists/{plain.id}")).json()
    assert (nothing["real_name"], nothing["born"], nothing["links"]) == (None, None, [])


async def test_clips_of_the_songs_of_the_artist_are_sorted_and_shown_once(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    thom = (await arrange(sessionmaker))["thom"]
    async with sessionmaker() as db, db.begin():
        songs = (
            await db.scalars(select(Song).order_by(Song.base_name))
        ).all()  # Guest, Own, Produced
        for song, views in zip(songs, (5, 50, 500), strict=True):
            song.view_count = views
        # one clip on two songs of the artist, one clip of a song the artist is not on
        db.add_all(
            [
                SongVideo(song_id=songs[0].id, url="https://y/a"),
                SongVideo(song_id=songs[1].id, url="https://y/a"),
                SongVideo(song_id=songs[2].id, url="https://y/b"),
                SongAudio(song_id=songs[2].id, provider="spotify", url="https://s/c"),
            ]
        )
        stranger = await make_song(db, "Stranger")
        db.add(SongVideo(song_id=stranger.id, url="https://y/d"))

    by_views = (await api.get(f"/api/v1/artists/{thom}/videos?sort=views")).json()

    assert [(v["url"], v["song_name"]) for v in by_views["items"]] == [
        ("https://y/b", "Produced"),
        ("https://y/a", "Own"),  # the song created first stands for the shared clip
    ]
    assert by_views["total"] == 2
    by_name = (await api.get(f"/api/v1/artists/{thom}/videos?sort=name")).json()
    assert [v["song_name"] for v in by_name["items"]] == ["Own", "Produced"]
