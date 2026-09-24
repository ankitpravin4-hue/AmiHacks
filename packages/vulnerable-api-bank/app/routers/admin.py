"""Admin audit — reachable without authentication."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.schemas import AuditOut

router = APIRouter(tags=["admin"])


@router.get("/admin/audit", response_model=AuditOut)
def admin_audit(db: Session = Depends(get_db)) -> AuditOut:
    """Return internal audit metrics.

    # VULN: broken authentication — no auth dependency, reachable by anyone.
    """
    total_accounts = db.scalar(select(func.count()).select_from(Account)) or 0
    total_held = db.scalar(select(func.coalesce(func.sum(Account.balance), 0.0))) or 0.0
    frozen = db.scalar(
        select(func.count()).select_from(Account).where(Account.is_frozen.is_(True))
    ) or 0
    return AuditOut(
        total_accounts=total_accounts,
        total_held_funds=float(total_held),
        frozen_accounts=int(frozen),
        pending_sar_filings=3,
        staff_notes="Wire desk: hold outbound > $10k pending BSA review.",
    )
