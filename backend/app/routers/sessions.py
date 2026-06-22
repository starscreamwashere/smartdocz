"""Session APIs — scaffolded in Milestone 1, implemented in Milestone 3.

All routes already enforce Clerk auth via `CurrentUser`, establishing the
ownership pattern (a user may only touch their own sessions).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser

router = APIRouter(prefix="/sessions", tags=["sessions"])

_NOT_YET = "Session persistence ships in Milestone 3."


@router.post("")
def create_session(user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("")
def list_sessions(user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/{session_id}")
def get_session(session_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.delete("/{session_id}")
def delete_session(session_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
