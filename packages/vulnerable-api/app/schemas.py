"""Pydantic request/response models. Some fields are intentionally over-exposed."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Email/password login body."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Bearer token issued after a successful login."""

    access_token: str
    token_type: str = "bearer"
    user_id: int


class UserOut(BaseModel):
    """User profile as returned by the API.

    Includes fields a correct API would never return to a peer customer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    password_hash: str
    is_admin: bool
    phone: str
    internal_notes: str


class UserUpdate(BaseModel):
    """Profile update body.

    `is_admin` is accepted on purpose so the mass-assignment detector
    can see the privileged field in the OpenAPI spec.
    """

    email: str | None = None
    phone: str | None = None
    is_admin: bool | None = Field(
        default=None,
        description="Privileged flag. A correct API must ignore this from clients.",
    )


class ProductOut(BaseModel):
    """Public catalog product — no sensitive fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: float


class OrderOut(BaseModel):
    """Order detail, including owner id and shipping address."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: int
    quantity: int
    total: float
    status: str
    shipping_address: str


class AdminStatsOut(BaseModel):
    """Internal store metrics."""

    total_users: int
    total_orders: int
    total_revenue: float
    pending_chargebacks: int


class HealthOut(BaseModel):
    """Liveness payload."""

    status: str
    service: str
