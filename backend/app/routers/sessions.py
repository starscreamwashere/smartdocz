"""Session APIs — Milestone 3: session persistence.

A user may create sessions, list their history (with message/file counts),
reopen one, and delete it. All routes enforce ownership via CurrentUser.
Deleting a session cascades its messages/files in Postgres and also clears the
session's vectors (Chroma) and raw files (disk).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.crud import create_session, get_owned_session, list_sessions_with_counts
from app.database import get_db
from app.schemas import SessionCreate, SessionOut, SessionSummary
from app.services import storage, vectorstore

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create(
    body: SessionCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SessionOut:
    session = create_session(db, user, title=body.title)
    return SessionOut.model_validate(session)


@router.get("", response_model=list[SessionSummary])
def list_sessions(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[SessionSummary]:
    rows = list_sessions_with_counts(db, user)
    return [
        SessionSummary(
            **SessionOut.model_validate(r["session"]).model_dump(),
            message_count=r["message_count"],
            file_count=r["file_count"],
        )
        for r in rows
    ]


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SessionOut:
    session = get_owned_session(db, user, session_id)
    return SessionOut.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    session = get_owned_session(db, user, session_id)
    # Clear external stores first; DB cascade handles messages/files rows.
    vectorstore.delete_session(session.id)
    storage.delete_session_dir(user.id, session.id)
    db.delete(session)
    db.commit()
