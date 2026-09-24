"""FastAPI application for the ShopAPI demo target."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import User
from app.routers import admin, auth, orders, products, users
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create tables and seed the demo dataset on first boot."""
    init_db()
    session = SessionLocal()
    try:
        has_users = session.scalar(select(User.id).limit(1))
        if has_users is None:
            import sys
            from pathlib import Path

            package_root = Path(__file__).resolve().parent.parent
            if str(package_root) not in sys.path:
                sys.path.insert(0, str(package_root))
            from seed import seed

            seed(session)
            session.commit()
    finally:
        session.close()
    yield


app = FastAPI(
    title="ShopAPI",
    description="Demo e-commerce API for local security testing only.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(admin.router)


@app.get("/healthz", response_model=HealthOut, tags=["ops"])
def healthz() -> HealthOut:
    """Liveness probe used by run scripts and later orchestration."""
    return HealthOut(status="ok", service="shopapi")
