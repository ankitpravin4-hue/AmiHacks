"""Account routes — scoped list is safe; object-level GET is not."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Account, User
from app.schemas import AccountOut, AccountPublic

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountPublic])
def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Account]:
    """List accounts for the authenticated caller only.

    Correctly scoped so the scanner can distinguish it from the BOLA
    object-level route below.
    """
    return list(db.scalars(select(Account).where(Account.owner_id == current_user.id)))


@router.get("/accounts/{account_id}", response_model=AccountOut)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountOut:
    """Return one account by id.

    Auth is required, but any authenticated caller may request any id.
    """
    _ = current_user
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    # VULN: BOLA — no ownership check. Any authenticated user can read
    # any other customer's account (e.g. alice GETs /accounts/201).
    # VULN: excessive data exposure — the response includes
    # balance_secret, kyc_notes, is_frozen, and internal_notes.
    return AccountOut(
        id=account.id,
        owner_id=account.owner_id,
        number=account.number,
        balance=account.balance,
        balance_secret=account.balance_secret,
        kyc_notes=account.kyc_notes,
        is_frozen=account.is_frozen,
        internal_notes=account.internal_notes,
        secret=account.balance_secret,
    )
