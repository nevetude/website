import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from music_backend.config import Settings, get_settings
from music_backend.main import create_app
from music_backend.models import Base
from tests.fakes import NAMES

BACKEND_ROOT = Path(__file__).parent.parent
TEST_DB = "music_test"


def database_url(name: str) -> URL:
    return make_url(get_settings().database_url).set(database=name)


async def recreate_database(name: str) -> None:
    engine = create_async_engine(
        database_url("postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    await engine.dispose()


def alembic_config(url: URL) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    return config


@pytest.fixture(autouse=True)
def _forget_fake_artist_names() -> None:
    NAMES.clear()


@pytest.fixture(scope="session")
def migrated_url() -> URL:
    """A fresh database built by the real migrations, so every test also exercises them."""
    asyncio.run(recreate_database(TEST_DB))
    url = database_url(TEST_DB)
    command.upgrade(alembic_config(url), "head")
    return url


@pytest.fixture
async def session(migrated_url: URL) -> AsyncIterator[AsyncSession]:
    """A session inside a transaction that is rolled back after the test."""
    engine = create_async_engine(migrated_url, poolclass=NullPool)
    async with engine.connect() as conn:
        outer = await conn.begin()
        async with AsyncSession(
            conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as db:
            yield db
        await outer.rollback()
    await engine.dispose()


@pytest.fixture
async def api(migrated_url: URL) -> AsyncIterator[AsyncClient]:
    """The real app (own sessions, background jobs) on the test database; tables are emptied afterwards."""
    settings = Settings(
        database_url=migrated_url.render_as_string(hide_password=False),
        genius_min_interval_s=0,
        genius_retry_backoff_s=0,
    )
    app = create_app(settings)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client
        await truncate_all_tables(migrated_url)


async def truncate_all_tables(url: URL) -> None:
    tables = ", ".join(f'"{name}"' for name in Base.metadata.tables)
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()


async def wait_for_job(
    client: AsyncClient, job_id: int, timeout_s: float = 5, until: tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Poll like the site does, until the job reaches one of `until` (default: any finished state)."""
    done = until or ("succeeded", "failed", "cancelled")
    deadline = asyncio.get_running_loop().time() + timeout_s
    while True:
        job: dict[str, Any] = (await client.get(f"/api/v1/imports/{job_id}")).json()
        if job["status"] in done:
            return job
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError(f"job {job_id} is {job['status']}, expected {done}")
        await asyncio.sleep(0.02)


@pytest.fixture
async def sessionmaker(migrated_url: URL) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Committing sessions on the test database, for arranging data that the app must see."""
    engine = create_async_engine(migrated_url, poolclass=NullPool)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
    await truncate_all_tables(migrated_url)
