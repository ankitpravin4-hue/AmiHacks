"""Public product catalog — intentionally safe."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductOut

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    """Return the public catalog. No auth, no sensitive fields."""
    return list(db.scalars(select(Product)))
