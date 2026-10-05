from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Team Tracker"
    environment: str = "development"
    secret_key: str
    database_url: str = "sqlite:///./team_tracker.db"
    upload_max_mb: int = 10
    session_minutes: int = 480
    secure_cookies: bool = False
    webhook_token: str | None = None
    cors_origins: str = "*"
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    seed_admin_name: str = "Initial Admin"
    # Opt-in recovery switch: re-applies the seed password/role to an existing admin on startup.
    seed_admin_reset: bool = False
    app_base_url: str = "http://localhost:8000"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()