"""Bearer-token authentication against the seeded token→user map."""

import hashlib

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Token, User

bearer_scheme = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    """Return a SHA-256 hex digest. Demo-only — not a production hasher."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Compare a plaintext password to a stored SHA-256 hash."""
    return hash_password(password) == password_hash


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve `Authorization: Bearer <token>` to a `User`."""
    row = db.get(Token, credentials.credentials)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not bound to a user",
        )
    return user
