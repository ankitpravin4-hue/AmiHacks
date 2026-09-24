"""Transaction routes — list and object GET are scoped; search is SQLi."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Account, Transaction, User
from app.schemas import TransactionOut

router = APIRouter(tags=["transactions"])


def _owned_account_ids(db: Session, user: User) -> list[int]:
    return list(db.scalars(select(Account.id).where(Account.owner_id == user.id)))


@router.get("/transactions", response_model=list[TransactionOut])
def list_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Transaction]:
    """List ledger lines for accounts the caller owns. Correctly scoped."""
    owned = _owned_account_ids(db, current_user)
    if not owned:
        return []
    return list(db.scalars(select(Transaction).where(Transaction.account_id.in_(owned))))


@router.get("/transactions/search", response_model=list[TransactionOut])
def search_transactions(q: str, db: Session = Depends(get_db)) -> list[TransactionOut]:
    """Search ledger memos. No auth — the existing SQLi detector sends no token.

    # VULN: SQL injection — `q` is concatenated into a raw SELECT. A payload
    # such as q=' OR '1'='1 bypasses the memo filter and returns every row.
    # SELECT-only: this handler never UPDATE / DELETE / DROP.
    """
    sql = (
        "SELECT id, account_id, amount, memo, created_at FROM transactions "
        f"WHERE memo LIKE '%{q}%'"
    )
    rows = db.execute(text(sql))
    return [TransactionOut.model_validate(row._mapping) for row in rows]


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Transaction:
    """Return one ledger line if the caller owns the parent account."""
    row = db.get(Transaction, transaction_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    account = db.get(Account, row.account_id)
    if account is None or account.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return row
