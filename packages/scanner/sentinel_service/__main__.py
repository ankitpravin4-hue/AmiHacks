"""`python -m sentinel_service` — listen on 127.0.0.1:8100 (not ShopAPI's 8000)."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """Boot the scanner service on a dedicated port."""
    host = os.getenv("SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICE_PORT", "8100"))
    uvicorn.run(
        "sentinel_service.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
