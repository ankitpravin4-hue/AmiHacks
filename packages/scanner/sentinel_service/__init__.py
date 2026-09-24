"""FastAPI wrapper around ScanEngine and SQLite storage."""

from sentinel_service.app import app, create_app

__all__ = ["app", "create_app"]
