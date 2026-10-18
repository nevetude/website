from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL

from music_backend.config import Settings
from music_backend.main import create_app


async def test_health_checks_the_database(migrated_url: URL) -> None:
    app = create_app(Settings(database_url=migrated_url.render_as_string(hide_password=False)))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
