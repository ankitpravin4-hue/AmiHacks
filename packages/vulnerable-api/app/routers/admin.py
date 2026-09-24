"""Admin metrics — reachable without authentication."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, User
from app.schemas import AdminStatsOut

router = APIRouter(tags=["admin"])


@router.get("/admin/stats", response_model=AdminStatsOut)
def admin_stats(db: Session = Depends(get_db)) -> AdminStatsOut:
    """Return internal store metrics.

    # VULN: broken authentication — no auth dependency, reachable by anyone.
    """
    # VULN: broken authentication — this admin route has no auth check.
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    total_orders = db.scalar(select(func.count()).select_from(Order)) or 0
    total_revenue = db.scalar(select(func.coalesce(func.sum(Order.total), 0.0))) or 0.0
    return AdminStatsOut(
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=float(total_revenue),
        pending_chargebacks=1,
    )
