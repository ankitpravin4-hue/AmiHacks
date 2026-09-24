"""Transfers — correctly scoped to accounts the caller owns."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Account, User
from app.schemas import TransferIn, TransferOut

router = APIRouter(tags=["transfers"])


@router.post("/transfers", response_model=TransferOut)
def create_transfer(
    payload: TransferIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransferOut:
    """Move funds from an account the caller owns. No privileged body fields."""
    source = db.get(Account, payload.from_account_id)
    dest = db.get(Account, payload.to_account_id)
    if source is None or dest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if source.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your account")
    if payload.amount <= 0 or source.balance < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid amount")
    source.balance -= payload.amount
    dest.balance += payload.amount
    db.commit()
    return TransferOut(
        from_account_id=source.id,
        to_account_id=dest.id,
        amount=payload.amount,
        status="posted",
    )
