"""Chat APIs — RAG question answering with conversation memory.

Question → (memory + recent turns) → embed → vector search (session-scoped) →
top-K → Gemini → grounded answer. Messages are persisted; a rolling memory
summary is refreshed periodically so follow-up questions resolve references.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud
from app.auth import CurrentUser
from app.crud import get_owned_session
from app.database import get_db
from app.models import Message, ModelRun
from app.schemas import ChatRequest, ChatResponse, MessageOut, SourceOut
from app.services import memory as memory_service
from app.services.embeddings import MissingApiKeyError, ProviderError, QuotaExceededError
from app.services.rag import answer_question

logger = logging.getLogger("smartdocz")
router = APIRouter(tags=["chat"])


def _maybe_update_memory(
    db: Session, session_id: uuid.UUID, prior: object | None
) -> None:
    """Best-effort rolling-summary refresh; never fails the chat response."""
    try:
        total = crud.count_messages(db, session_id)
        if not memory_service.should_update_summary(total):
            return
        turns = [(m.role, m.content) for m in crud.all_messages(db, session_id)]
        prior_text = prior.summary_text if prior else None  # type: ignore[attr-defined]
        new_text = memory_service.summarize_conversation(turns, prior_summary=prior_text)
        version = (prior.summary_version + 1) if prior else 1  # type: ignore[attr-defined]
        crud.add_memory_summary(db, session_id, new_text, version)
    except Exception:  # noqa: BLE001 — memory is best-effort
        logger.warning("Memory summary update failed for session %s", session_id, exc_info=True)


@router.post("/chat", response_model=ChatResponse)
def send_message(
    body: ChatRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    if not body.message.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message cannot be empty.")
    session = get_owned_session(db, user, body.session_id)

    # Gather conversation context BEFORE recording the new question.
    prior_memory = crud.get_latest_memory(db, session.id)
    history = [
        (m.role, m.content)
        for m in crud.recent_messages(db, session.id, memory_service.RECENT_HISTORY_LIMIT)
    ]

    # Persist the user's message.
    user_msg = Message(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)

    try:
        answer = answer_question(
            body.message,
            session_id=session.id,
            history=history,
            memory_summary=prior_memory.summary_text if prior_memory else None,
        )
    except MissingApiKeyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except QuotaExceededError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    # Persist the assistant's answer.
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=answer.text,
        model_provider=answer.llm.provider,
    )
    db.add(assistant_msg)

    # Log the model run (provider used, latency, tokens, estimated cost).
    if answer.has_context:
        db.add(
            ModelRun(
                session_id=session.id,
                provider=answer.llm.provider,
                model=answer.llm.model,
                latency_ms=answer.llm.latency_ms,
                tokens_used=answer.llm.tokens_used,
                estimated_cost=answer.llm.estimated_cost,
            )
        )

    session.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

    # Refresh the rolling conversation memory (best effort, every N messages).
    _maybe_update_memory(db, session.id, prior_memory)

    return ChatResponse(
        session_id=session.id,
        message_id=assistant_msg.id,
        answer=answer.text,
        sources=[SourceOut(**vars(s)) for s in answer.sources],
        has_context=answer.has_context,
        model_provider=answer.llm.provider,
        model=answer.llm.model,
    )


@router.get("/messages/{session_id}", response_model=list[MessageOut])
def get_messages(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[MessageOut]:
    get_owned_session(db, user, session_id)
    rows = db.scalars(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    ).all()
    return [MessageOut.model_validate(r) for r in rows]
