"""User profile routes — seeded with BOLA, data exposure, and mass assignment."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Return a user record.

    Auth is required, but any authenticated caller may request any id.
    """
    _ = current_user  # authenticated, but unused for authorization
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # VULN: BOLA — no ownership check. Any authenticated user can read
    # any other user (e.g. alice GETs /users/2 and receives bob).
    # VULN: excessive data exposure — the response schema includes
    # password_hash, internal_notes, and is_admin.
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update a user profile, including privileged fields from the body."""
    _ = current_user
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    # VULN: mass assignment — `is_admin` is taken from the request body
    # and written to the user row. A non-admin can escalate privileges.
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    db.commit()
    db.refresh(user)
    return user
