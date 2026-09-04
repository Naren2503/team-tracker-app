from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Team Tracker"
    environment: str = "development"
    secret_key: str
    database_url: str = "sqlite:///./team_tracker.db"
    upload_max_mb: int = 10
    session_minutes: int = 480
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    seed_admin_name: str = "Initial Admin"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
