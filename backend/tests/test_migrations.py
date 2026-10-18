import asyncio

from alembic import command

from tests.conftest import alembic_config, database_url, recreate_database


def test_migrations_round_trip_and_match_models() -> None:
    """upgrade -> check (models and database agree) -> downgrade -> upgrade, on a throwaway database."""
    asyncio.run(recreate_database("music_migration_test"))
    config = alembic_config(database_url("music_migration_test"))

    command.upgrade(config, "head")
    command.check(config)  # raises if the models differ from the migrated schema
    command.downgrade(config, "base")
    command.upgrade(config, "head")
