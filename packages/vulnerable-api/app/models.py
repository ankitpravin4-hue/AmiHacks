"""SQLAlchemy models for the demo shop."""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all shop tables."""


class User(Base):
    """A shop account. `internal_notes` is staff-only in a correct API."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    internal_notes: Mapped[str] = mapped_column(Text, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    tokens: Mapped[list["Token"]] = relationship(back_populates="user")


class Token(Base):
    """Predictable bearer token → user mapping (intentional demo weakness)."""

    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user: Mapped[User] = relationship(back_populates="tokens")


class Product(Base):
    """Public catalog item."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="product")


class Order(Base):
    """A customer's order. Contains PII in `shipping_address`."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship(back_populates="orders")
    product: Mapped[Product] = relationship(back_populates="orders")
