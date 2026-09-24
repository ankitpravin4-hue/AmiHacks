"""Login route — issues a bearer token with no throttling."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_password
from app.database import get_db
from app.models import Token, User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Authenticate with email/password and return a bearer token.

    # VULN: no rate limiting — this endpoint accepts unlimited attempts
    # and is therefore brute-forceable.
    """
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = db.scalar(select(Token).where(Token.user_id == user.id))
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no issued token",
        )
    return LoginResponse(access_token=token.token, user_id=user.id)
