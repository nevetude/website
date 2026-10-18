"""Wipe the local database and build it again from the migrations: a clean start for an import.

    uv run python scripts/reset_db.py          # asks first
    uv run python scripts/reset_db.py --yes    # does not ask

Every table and every row is lost. Stop the backend and any running import first. It refuses a database
that is not on this machine. If the database is down it starts the compose service by itself.
"""

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from music_backend.config import get_settings

BACKEND = Path(__file__).resolve().parent.parent
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
WAIT_FOR_DB_S = 40


async def wipe(url: str) -> None:
    engine = create_async_engine(url)
    try:
        for attempt in range(WAIT_FOR_DB_S):
            try:
                async with engine.begin() as connection:
                    await connection.execute(text("DROP SCHEMA public CASCADE"))
                    await connection.execute(text("CREATE SCHEMA public"))
                return
            except OSError:
                if (
                    attempt == 0
                ):  # nothing listens: the container was stopped (WSL restarts do that)
                    print("The database does not answer, starting it (docker compose up -d db)...")
                    docker = await asyncio.create_subprocess_exec(
                        shutil.which("docker") or "docker",
                        *("compose", "up", "-d", "db"),
                        cwd=BACKEND.parent,
                    )
                    if await docker.wait():
                        raise SystemExit("docker compose up -d db failed") from None
                await asyncio.sleep(1)
        raise SystemExit(f"The database did not come up in {WAIT_FOR_DB_S} s")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args()

    url = get_settings().database_url
    target = make_url(url)
    if target.host not in LOCAL_HOSTS:
        raise SystemExit(f"Refusing to wipe {target.host}: this is for the local database only")
    if not args.yes:
        answer = input(f"Delete ALL data in database '{target.database}' on {target.host}? [y/N] ")
        if answer.strip().lower() != "y":
            raise SystemExit("Cancelled")

    asyncio.run(wipe(url))
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(config, "head")
    print(
        f"Done: '{target.database}' is empty and migrated. Start the backend and import.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
