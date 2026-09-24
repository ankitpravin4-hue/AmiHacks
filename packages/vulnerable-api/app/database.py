"""SQLAlchemy engine and session helpers."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base


def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent directory for a file-backed SQLite URL."""
    if not url.startswith("sqlite:///"):
        return
    db_path = Path(url.removeprefix("sqlite:///"))
    if db_path.parent and str(db_path.parent) not in {".", ""}:
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create tables if they do not exist."""
    _ensure_sqlite_dir(settings.database_url)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
