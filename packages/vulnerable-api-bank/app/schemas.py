"""Pydantic request/response models. Account detail is intentionally over-exposed."""

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Email/password login body."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Bearer token issued after a successful login."""

    access_token: str
    token_type: str = "bearer"
    user_id: int


class AccountPublic(BaseModel):
    """Caller-scoped list row — no staff or secret fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    balance: float


class AccountOut(BaseModel):
    """Account detail as returned by GET /accounts/{id}.

    Includes fields a correct bank API would never return to a peer customer.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    number: str
    balance: float
    balance_secret: str
    kyc_notes: str
    is_frozen: bool
    internal_notes: str
    secret: str


class TransactionOut(BaseModel):
    """Ledger line — no staff secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount: float
    memo: str
    created_at: str


class TransferIn(BaseModel):
    """Move funds between accounts the caller owns."""

    from_account_id: int
    to_account_id: int
    amount: float


class TransferOut(BaseModel):
    """Transfer receipt."""

    from_account_id: int
    to_account_id: int
    amount: float
    status: str


class RateOut(BaseModel):
    """Public FX quote — no auth, no secrets."""

    pair: str
    rate: float


class AuditOut(BaseModel):
    """Internal audit snapshot."""

    total_accounts: int
    total_held_funds: float
    frozen_accounts: int
    pending_sar_filings: int
    staff_notes: str


class HealthOut(BaseModel):
    """Liveness payload."""

    status: str
    service: str
