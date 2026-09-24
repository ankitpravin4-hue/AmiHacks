"""Seed users, predictable tokens, products, and orders.

Run standalone (`python seed.py`) or from the app lifespan on an empty DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# Allow `python seed.py` from this directory.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.auth import hash_password
from app.models import Order, Product, Token, User

# Demo accounts — passwords and tokens are intentionally weak/predictable.
DEMO_USERS: list[dict[str, object]] = [
    {
        "id": 1,
        "email": "alice@shop.test",
        "password": "alice123",
        "is_admin": False,
        "phone": "+1-555-0101",
        "internal_notes": "VIP customer. Card on file ending 4242. Do not mention in tickets.",
        "token": "tok_alice",
    },
    {
        "id": 2,
        "email": "bob@shop.test",
        "password": "bob123",
        "is_admin": False,
        "phone": "+1-555-0102",
        "internal_notes": "Chargeback risk — hold refunds pending manager review.",
        "token": "tok_bob",
    },
    {
        "id": 3,
        "email": "admin@shop.test",
        "password": "admin123",
        "is_admin": True,
        "phone": "+1-555-0100",
        "internal_notes": "Platform administrator. Full PII access.",
        "token": "tok_admin",
    },
]

DEMO_PRODUCTS: list[dict[str, object]] = [
    {
        "id": 1,
        "name": "Wireless Mouse",
        "description": "Ergonomic 2.4 GHz mouse",
        "price": 29.99,
    },
    {
        "id": 2,
        "name": "Mechanical Keyboard",
        "description": "Hot-swap TKL keyboard",
        "price": 129.00,
    },
    {
        "id": 3,
        "name": "USB-C Hub",
        "description": "7-in-1 HDMI + PD hub",
        "price": 79.50,
    },
    {
        "id": 4,
        "name": "1080p Webcam",
        "description": "Clip-on webcam with mic",
        "price": 59.00,
    },
]

# Distinct ids so a BOLA demo is obvious: alice 101/102, bob 201/202.
DEMO_ORDERS: list[dict[str, object]] = [
    {
        "id": 101,
        "user_id": 1,
        "product_id": 1,
        "quantity": 1,
        "total": 29.99,
        "status": "shipped",
        "shipping_address": "14 Pine St, Apt 3, Springfield",
    },
    {
        "id": 102,
        "user_id": 1,
        "product_id": 2,
        "quantity": 1,
        "total": 129.00,
        "status": "processing",
        "shipping_address": "14 Pine St, Apt 3, Springfield",
    },
    {
        "id": 201,
        "user_id": 2,
        "product_id": 3,
        "quantity": 2,
        "total": 159.00,
        "status": "shipped",
        "shipping_address": "88 Harbor Rd, Riverton",
    },
    {
        "id": 202,
        "user_id": 2,
        "product_id": 4,
        "quantity": 1,
        "total": 59.00,
        "status": "delivered",
        "shipping_address": "88 Harbor Rd, Riverton",
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
                phone=str(row["phone"]),
                internal_notes=str(row["internal_notes"]),
            )
        )
        session.add(Token(token=str(row["token"]), user_id=int(row["id"])))  # type: ignore[arg-type]

    for row in DEMO_PRODUCTS:
        session.add(Product(**row))  # type: ignore[arg-type]

    for row in DEMO_ORDERS:
        session.add(Order(**row))  # type: ignore[arg-type]

    session.flush()


def main() -> None:
    """CLI: create tables and seed a fresh database."""
    from app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        seed(session)
        session.commit()
        print("Seeded ShopAPI demo data (alice, bob, admin, orders, products).")
    finally:
        session.close()


if __name__ == "__main__":
    main()
