"""Application settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "dev-insecure-change-me-in-production"
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'mood_recipes.db'}"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "access_token"

    debug: bool = False

    reset_token_expire_minutes: int = 60

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    public_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
