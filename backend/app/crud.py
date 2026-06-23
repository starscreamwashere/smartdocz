"""Small data-access helpers shared across routers."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatSession, User


def create_session(db: Session, user: User, title: str | None = None) -> ChatSession:
    session = ChatSession(user_id=user.id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_owned_session(
    db: Session, user: User, session_id: uuid.UUID
) -> ChatSession:
    """Fetch a session, enforcing that it belongs to the current user.

    Returns 404 (not 403) for someone else's session so we don't leak existence.
    """
    session = db.scalar(select(ChatSession).where(ChatSession.id == session_id))
    if session is None or session.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    return session
