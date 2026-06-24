"""Chat APIs — Milestone 2: RAG question answering.

Question → embed → vector search (session-scoped) → top-K → Gemini → grounded
answer. User and assistant messages are persisted; each generation is logged to
model_runs for later analytics (Milestone 6).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.crud import get_owned_session
from app.database import get_db
from app.models import Message, ModelRun
from app.schemas import ChatRequest, ChatResponse, MessageOut, SourceOut
from app.services.embeddings import MissingApiKeyError, ProviderError, QuotaExceededError
from app.services.rag import answer_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def send_message(
    body: ChatRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ChatResponse:
    if not body.message.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Message cannot be empty.")
    session = get_owned_session(db, user, body.session_id)

    # Persist the user's message.
    user_msg = Message(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)

    try:
        answer = answer_question(body.message, session_id=session.id)
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

    # Log the model run (tokens/cost tracked from Milestone 7).
    if answer.has_context:
        db.add(
            ModelRun(
                session_id=session.id,
                provider=answer.llm.provider,
                model=answer.llm.model,
                latency_ms=answer.llm.latency_ms,
            )
        )

    session.last_message_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

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
