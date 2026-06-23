"""Small data-access helpers shared across routers."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ChatSession, Message, UploadedFile, User


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


def list_sessions_with_counts(db: Session, user: User) -> list[dict]:
    """Return the user's sessions (newest activity first) with message/file counts."""
    msg_count = (
        select(Message.session_id, func.count().label("n"))
        .group_by(Message.session_id)
        .subquery()
    )
    file_count = (
        select(UploadedFile.session_id, func.count().label("n"))
        .group_by(UploadedFile.session_id)
        .subquery()
    )
    rows = db.execute(
        select(
            ChatSession,
            func.coalesce(msg_count.c.n, 0),
            func.coalesce(file_count.c.n, 0),
        )
        .outerjoin(msg_count, msg_count.c.session_id == ChatSession.id)
        .outerjoin(file_count, file_count.c.session_id == ChatSession.id)
        .where(ChatSession.user_id == user.id)
        .order_by(
            func.coalesce(ChatSession.last_message_at, ChatSession.created_at).desc()
        )
    ).all()
    return [
        {"session": s, "message_count": m, "file_count": f} for s, m, f in rows
    ]
