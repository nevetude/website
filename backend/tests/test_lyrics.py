from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.config import Settings
from music_backend.lyrics import Stanza, parse_lyrics
from music_backend.main import create_app
from tests.conftest import truncate_all_tables
from tests.factories import make_song

type SessionMaker = async_sessionmaker[AsyncSession]

# Made up for the tests, like every text in them.
TEXT = """[Verse 1: Someone]
first line
second line

[Chorus]
sung line

loose line after a gap
"""


def test_names_open_stanzas_and_a_blank_line_closes_them() -> None:
    assert parse_lyrics(TEXT) == [
        Stanza("[Verse 1: Someone]", ["first line", "second line"]),
        Stanza("[Chorus]", ["sung line"]),
        Stanza(None, ["loose line after a gap"]),
    ]


async def test_the_text_comes_from_the_file_of_the_genius_id(
    migrated_url: URL, sessionmaker: SessionMaker, tmp_path: Path
) -> None:
    async with sessionmaker() as db:
        written = await make_song(db, "Written", genius_id=77)
        missing = await make_song(db, "Missing", genius_id=78)
        manual = await make_song(db, "Manual")
        await db.commit()
    (tmp_path / "77.txt").write_text(TEXT, encoding="utf-8")
    settings = Settings(
        database_url=migrated_url.render_as_string(hide_password=False), lyrics_dir=tmp_path
    )

    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        got = (await client.get(f"/api/v1/songs/{written.id}/lyrics")).json()
        absent = (await client.get(f"/api/v1/songs/{missing.id}/lyrics")).json()
        no_id = (await client.get(f"/api/v1/songs/{manual.id}/lyrics")).json()
        unknown = (await client.get("/api/v1/songs/999999/lyrics")).status_code
        (tmp_path / "demo.txt").write_text("[Demo]\nshown everywhere\n", encoding="utf-8")
        shared = [
            (await client.get(f"/api/v1/songs/{song.id}/lyrics")).json()["stanzas"][0]["lines"]
            for song in (written, missing, manual)
        ]
    await truncate_all_tables(migrated_url)

    assert (got["stanzas"][0]["title"], got["stanzas"][0]["lines"]) == (
        "[Verse 1: Someone]",
        ["first line", "second line"],
    )
    assert (absent, no_id, unknown) == (None, None, 404)
    # With a demo file every song without a file of its own shows it; a song with one keeps its own.
    assert shared == [["first line", "second line"], ["shown everywhere"], ["shown everywhere"]]
