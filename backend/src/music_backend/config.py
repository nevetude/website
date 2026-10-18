from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local dev default matching compose.yaml; override with DATABASE_URL.
    database_url: str = "postgresql+asyncpg://music:music@localhost:5432/music"
    genius_base_url: str = "https://genius.com/api"
    # Politeness towards Genius: minimum pause between two requests.
    # 5 requests a second. The official API announces 10 000 an hour (x-ratelimit-limit, 2.8 a second);
    # the public API publishes no limit, so this is a bet; a 429 stops the import (see RateLimitedError).
    genius_min_interval_s: float = 0.2
    # Pause before the first retry of a failed request; it grows with each further attempt.
    genius_retry_backoff_s: float = 2.0
    # Local-only shortcut: every request acts as the admin user. Turn off when real login exists.
    dev_auto_login: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
