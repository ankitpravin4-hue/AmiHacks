"""Order routes — one BOLA endpoint and one correctly scoped list."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Order, User
from app.schemas import OrderOut

router = APIRouter(tags=["orders"])


@router.get("/orders", response_model=list[OrderOut])
def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Order]:
    """List orders for the authenticated caller only.

    This endpoint is *correctly scoped* so the scanner must distinguish
    it from the BOLA object-level route below.
    """
    return list(db.scalars(select(Order).where(Order.user_id == current_user.id)))


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    """Return a single order by id."""
    _ = current_user
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    # VULN: BOLA — no ownership check. Any authenticated user can read
    # any order (e.g. alice GETs /orders/201 and receives bob's order,
    # including shipping_address).
    return order
