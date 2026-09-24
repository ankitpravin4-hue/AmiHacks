"""Public product catalog — list is safe; search is a seeded SQLi demo."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductOut

router = APIRouter(tags=["products"])


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    """Return the public catalog. No auth, no sensitive fields."""
    return list(db.scalars(select(Product)))


@router.get("/products/search", response_model=list[ProductOut])
def search_products(q: str, db: Session = Depends(get_db)) -> list[ProductOut]:
    """Search the catalog by product name.

    # VULN: SQL injection — `q` is concatenated into a raw SELECT. A payload
    # such as q=' OR '1'='1 bypasses the name filter and returns every row.
    # SELECT-only: this handler never UPDATE / DELETE / DROP.
    """
    sql = (
        "SELECT id, name, description, price FROM products "
        f"WHERE name LIKE '%{q}%'"
    )
    rows = db.execute(text(sql))
    return [ProductOut.model_validate(row._mapping) for row in rows]
