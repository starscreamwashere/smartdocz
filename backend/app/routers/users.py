"""User APIs."""
from __future__ import annotations

from fastapi import APIRouter

from app.auth import CurrentUser
from app.schemas import UserOut

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    """Return the current authenticated user (upserted on first request)."""
    return UserOut.model_validate(user)
