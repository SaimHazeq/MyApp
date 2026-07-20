"""
Central application configuration.

Every tunable value (secrets, provider API keys, storage paths, feature flags)
is read from the environment so the same codebase runs unchanged across
local development, staging and production. Copy `.env.example` to `.env`
and fill in real values before deploying.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    APP_NAME: str = "AI Cartoon Movie Maker"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_32_CHAR_MIN"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24        # 24 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    JWT_ALGORITHM: str = "HS256"

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Database ---
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/storage/app.db"

    # --- Background jobs (Celery/Redis). Falls back to an in-process
    # thread-pool worker (see workers/generation_worker.py) if Redis
    # is not reachable, so the app still works with zero extra infra. ---
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False

    # --- Storage ---
    STORAGE_ROOT: Path = BASE_DIR / "storage"
    PROJECTS_DIR: Path = BASE_DIR / "storage" / "projects"
    RENDERS_DIR: Path = BASE_DIR / "storage" / "renders"
    TEMP_DIR: Path = BASE_DIR / "storage" / "temp"
    MAX_UPLOAD_MB: int = 25

    # --- Rendering defaults ---
    DEFAULT_RESOLUTION: str = "1920x1080"
    DEFAULT_FPS: int = 24
    MAX_MOVIE_MINUTES: int = 30

    # --- AI provider integration (optional). Leave blank to use the
    # built-in offline placeholder engines so the pipeline always runs. ---
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    IMAGE_GEN_PROVIDER: str = "placeholder"   # placeholder | stability | openai
    VOICE_PROVIDER: str = "placeholder"       # placeholder | elevenlabs | openai
    MUSIC_PROVIDER: str = "placeholder"       # placeholder | elevenlabs

    def ensure_dirs(self) -> None:
        for d in (self.STORAGE_ROOT, self.PROJECTS_DIR, self.RENDERS_DIR, self.TEMP_DIR):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
