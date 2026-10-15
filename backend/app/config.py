from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    """Optional runtime settings loaded from backend/.env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str | None = None
    SECRET_KEY: str | None = None


settings = Settings()
