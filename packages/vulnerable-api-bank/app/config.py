"""Runtime configuration for the BankAPI demo target."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PACKAGE_ROOT / "data" / "bank.db"


class Settings(BaseSettings):
    """Host, port, and SQLite location. Overridable via env / `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(PACKAGE_ROOT.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH}"


settings = Settings()
