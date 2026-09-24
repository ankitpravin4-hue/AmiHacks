"""Seed users, tokens, accounts, and transactions.

Run standalone (`python seed.py`) or from the app lifespan on an empty DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.auth import hash_password
from app.models import Account, Token, Transaction, User

DEMO_USERS: list[dict[str, object]] = [
    {
        "id": 1,
        "email": "alice@bank.test",
        "password": "alice123",
        "is_admin": False,
        "full_name": "Alice Rivera",
        "token": "tok_bank_alice",
    },
    {
        "id": 2,
        "email": "bob@bank.test",
        "password": "bob123",
        "is_admin": False,
        "full_name": "Bob Chen",
        "token": "tok_bank_bob",
    },
    {
        "id": 3,
        "email": "admin@bank.test",
        "password": "admin123",
        "is_admin": True,
        "full_name": "Ira Admin",
        "token": "tok_bank_admin",
    },
]

DEMO_ACCOUNTS: list[dict[str, object]] = [
    {
        "id": 101,
        "owner_id": 1,
        "number": "1001-ALICE",
        "balance": 4280.55,
        "balance_secret": "ledger-alice-9f3a",
        "kyc_notes": "Source of funds: payroll. Watch large outbound wires.",
        "is_frozen": False,
        "internal_notes": "Source of funds: payroll. Watch large outbound wires.",
    },
    {
        "id": 201,
        "owner_id": 2,
        "number": "2001-BOB",
        "balance": 1190.00,
        "balance_secret": "ledger-bob-c21e",
        "kyc_notes": "PEP-adjacent. Enhanced due diligence on file.",
        "is_frozen": True,
        "internal_notes": "PEP-adjacent. Enhanced due diligence on file.",
    },
    {
        "id": 301,
        "owner_id": 3,
        "number": "3001-OPS",
        "balance": 50000.00,
        "balance_secret": "ledger-ops-aa00",
        "kyc_notes": "Internal operations float. Staff only.",
        "is_frozen": False,
        "internal_notes": "Internal operations float. Staff only.",
    },
]

DEMO_TRANSACTIONS: list[dict[str, object]] = [
    {
        "id": 1001,
        "account_id": 101,
        "amount": -85.00,
        "memo": "rent auto-pay",
        "created_at": "2026-09-01",
    },
    {
        "id": 1002,
        "account_id": 101,
        "amount": 2100.00,
        "memo": "payroll deposit",
        "created_at": "2026-09-05",
    },
    {
        "id": 2001,
        "account_id": 201,
        "amount": -40.00,
        "memo": "atm withdrawal",
        "created_at": "2026-09-03",
    },
    {
        "id": 2002,
        "account_id": 201,
        "amount": 50.00,
        "memo": "refund",
        "created_at": "2026-09-08",
    },
]


def seed(session: Session) -> None:
    """Insert demo rows if the users table is empty. Idempotent."""
    existing = session.scalar(select(User.id).limit(1))
    if existing is not None:
        return

    for row in DEMO_USERS:
        session.add(
            User(
                id=int(row["id"]),  # type: ignore[arg-type]
                email=str(row["email"]),
                password_hash=hash_password(str(row["password"])),
                is_admin=bool(row["is_admin"]),
                full_name=str(row["full_name"]),
            )
        )
        session.add(Token(token=str(row["token"]), user_id=int(row["id"])))  # type: ignore[arg-type]

    for row in DEMO_ACCOUNTS:
        session.add(Account(**row))  # type: ignore[arg-type]

    for row in DEMO_TRANSACTIONS:
        session.add(Transaction(**row))  # type: ignore[arg-type]

    session.flush()


def main() -> None:
    """CLI: create tables and seed a fresh database."""
    from app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        seed(session)
        session.commit()
        print("Seeded BankAPI demo data (alice, bob, admin, accounts, transactions).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
