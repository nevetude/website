from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.enums import AlbumRelationType, ImportKind, JobStatus, SongArtistRole
from music_backend.models import (
    AlbumArtist,
    AlbumCoverArt,
    AlbumCredit,
    AlbumRelationship,
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
    """Two discs: Opener and Closer on the first, Bonus on the second (a guest sings on it)."""
    async with sessionmaker() as db:
        main = await make_artist(db, "Main", genius_id=1)
        guest = await make_artist(db, "Guest", genius_id=2)
        producer = await make_artist(db, "Producer", genius_id=3)
        label = await make_artist(db, "Label Co", genius_id=4)
        album = await make_album(
            db,
            "Record",
            genius_id=100,
            variant="Deluxe",
            is_released=False,
            cover_secondary_color="#112233",
        )
        deluxe = await make_album(db, "Record Deluxe", genius_id=101)
        roles = {name: CreditRole(name=name) for name in ("Producer", "Label")}
        db.add_all(roles.values())
        await db.flush()

        rock = Genre(name="Rock", base_name="Rock")
        db.add(rock)
        await db.flush()
        opener = await make_song(db, "Opener", genre_id=rock.id)
        closer = await make_song(db, "Closer")
        bonus = await make_song(db, "Bonus")
        await place(db, album, closer, position=2, disc_number=1, is_primary=True)
        await place(db, album, opener, position=1, disc_number=1)
        await place(db, album, bonus, position=1, disc_number=2)
        db.add_all(
            [
                AlbumArtist(album_id=album.id, artist_id=main.id, position=1),
                SongArtist(song_id=opener.id, artist_id=main.id, role=SongArtistRole.PRIMARY),
                SongArtist(song_id=bonus.id, artist_id=main.id, role=SongArtistRole.PRIMARY),
                SongArtist(song_id=bonus.id, artist_id=guest.id, role=SongArtistRole.FEATURED),
                AlbumCredit(album_id=album.id, artist_id=label.id, role_id=roles["Label"].id),
                SongCredit(song_id=opener.id, artist_id=producer.id, role_id=roles["Producer"].id),
                SongCredit(song_id=bonus.id, artist_id=producer.id, role_id=roles["Producer"].id),
                AlbumCoverArt(
                    genius_id=7,
                    album_id=album.id,
                    position=1,
                    image_url="https://img/1.jpg",
                    thumbnail_image_url="https://img/1t.jpg",
                    genius_url="https://genius.com/a",
                ),
                AlbumRelationship(
                    album_id=deluxe.id,
                    related_album_id=album.id,
                    type=AlbumRelationType.DELUXE_EDITION_OF,
                ),
                ImportJob(kind=ImportKind.ALBUM, genius_id=100, status=JobStatus.SUCCEEDED),
            ]
        )
        await db.commit()
        return {"album": album.id, "deluxe": deluxe.id, "main": main.id}


async def test_the_album_with_everything_around_it(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    detail = (await api.get(f"/api/v1/albums/{ids['album']}")).json()

    assert (detail["base_name"], detail["variant"], detail["is_released"]) == (
        "Record",
        "Deluxe",
        False,
    )
    assert [a["base_name"] for a in detail["artists"]] == ["Main"]
    assert (detail["genres"], detail["cover_secondary_color"]) == (["Rock"], "#112233")
    assert [c["image_url"] for c in detail["covers"]] == ["https://img/1.jpg"]
    assert (detail["tracks_count"], detail["discs_count"]) == (3, 2)
    assert [(j["kind"], j["status"]) for j in detail["imports"]] == [("album", "succeeded")]
    # the album's own credits come first, then the songs' credits with the number of tracks
    assert [
        (
            g["role"],
            g["from_album"],
            [(c["artist"]["base_name"], c["tracks"]) for c in g["artists"]],
        )
        for g in detail["credits"]
    ] == [
        ("Label", True, [("Label Co", None)]),
        ("Producer", False, [("Producer", 2)]),
    ]
    # this album is the one the deluxe edition points at: "deluxe editions"
    assert [
        (r["type"], r["inverse"], [a["base_name"] for a in r["albums"]]) for r in detail["related"]
    ] == [("deluxe_edition_of", True, ["Record Deluxe"])]
    deluxe = (await api.get(f"/api/v1/albums/{ids['deluxe']}")).json()
    assert [(r["inverse"], [a["base_name"] for a in r["albums"]]) for r in deluxe["related"]] == [
        (False, ["Record"])
    ]


async def test_tracks_are_in_the_order_of_the_discs(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)

    tracks = (await api.get(f"/api/v1/albums/{ids['album']}/tracks")).json()

    assert [(t["disc_number"], t["position"], t["base_name"]) for t in tracks] == [
        (1, 1, "Opener"),
        (1, 2, "Closer"),
        (2, 1, "Bonus"),
    ]
    bonus = tracks[2]
    assert (
        [a["base_name"] for a in bonus["artists"]],
        [a["base_name"] for a in bonus["featured"]],
    ) == (
        ["Main"],
        ["Guest"],
    )
    assert tracks[1]["is_primary"] is True
    assert [[p["base_name"] for p in t["producers"]] for t in tracks] == [
        ["Producer"],
        [],
        ["Producer"],
    ]


async def test_an_unknown_album_is_a_404(api: AsyncClient) -> None:
    for tail in ("", "/tracks", "/raw"):
        assert (await api.get(f"/api/v1/albums/999{tail}")).status_code == 404


async def test_the_description_tree_and_where_its_links_lead(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    def link(path: str) -> dict[str, object]:
        return {
            "tag": "a",
            "attributes": {"href": f"https://genius.com{path}"},
            "data": {"api_path": path},
            "children": ["x"],
        }

    tree = {
        "tag": "root",
        "children": [
            {
                "tag": "p",
                "children": [
                    link("/artists/10"),
                    link("/artists/99"),
                    link("/songs/5"),
                    link("/albums/20"),
                ],
            }
        ],
    }
    async with sessionmaker() as db:
        await make_artist(db, "Ours", genius_id=10)
        other = await make_album(db, "Other", genius_id=20)
        album = await make_album(db, "Album", genius_id=30)
        body = {"description_annotation": {"annotations": [{"body": {"dom": tree}}]}}
        db.add(GeniusResponse(entity_type="album", entity_id=album.id, raw=body))
        plain = await make_album(db, "Imported long ago", genius_id=31)  # a response without a tree
        db.add(
            GeniusResponse(
                entity_type="album",
                entity_id=plain.id,
                raw={"description_annotation": {"annotations": [{"body": {"plain": "old"}}]}},
            )
        )
        await db.commit()

    detail = (await api.get(f"/api/v1/albums/{album.id}")).json()

    assert detail["description_dom"]["children"][0]["children"][0]["data"] == {
        "api_path": "/artists/10"
    }
    refs = {(r["api_path"], r["kind"]) for r in detail["description_refs"]}
    assert refs == {
        ("/artists/10", "artist"),
        ("/albums/20", "album"),
    }  # not /artists/99, not a song
    assert {r["id"] for r in detail["description_refs"] if r["kind"] == "album"} == {other.id}
    old = (await api.get(f"/api/v1/albums/{plain.id}")).json()
    assert (old["description_dom"], old["description_refs"]) == (None, [])


async def test_videos_are_the_clips_of_the_songs_in_track_order(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    ids = await arrange(sessionmaker)
    async with sessionmaker() as db:
        songs = {s.base_name: s.id for s in (await db.scalars(select(Song))).all()}
        db.add_all(
            [
                SongVideo(song_id=songs["Bonus"], url="https://y/b"),
                SongVideo(song_id=songs["Opener"], url="https://y/o"),
                # the same clip on two songs is shown once; audio is not a clip
                SongVideo(song_id=songs["Closer"], url="https://y/o"),
                SongAudio(song_id=songs["Closer"], provider="spotify", url="https://s/c"),
            ]
        )
        await db.commit()

    videos = (await api.get(f"/api/v1/albums/{ids['album']}/videos")).json()

    assert [(v["song_name"], v["url"]) for v in videos] == [
        ("Opener", "https://y/o"),
        ("Bonus", "https://y/b"),
    ]
    # the date of the song, as the tracklist knows it (the factory gives no date)
    assert [(v["release_date"], v["release_date_precision"]) for v in videos] == [(None, None)] * 2
    assert (await api.get("/api/v1/albums/999999/videos")).status_code == 404
