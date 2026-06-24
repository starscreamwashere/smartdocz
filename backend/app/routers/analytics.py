"""Analytics APIs — Milestone 6: RAGAS-style answer evaluation.

Evaluate a specific assistant answer against a user-supplied reference answer.
We recover the question (the preceding user message) and re-retrieve the
session's context, then score Faithfulness, Answer Relevancy, and Context
Precision and store the result.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.auth import CurrentUser
from app.config import get_settings
from app.crud import get_owned_session
from app.database import get_db
from app.models import Message
from app.schemas import AnalyticsOut, EvaluateRequest
from app.services import evaluation, vectorstore
from app.services.embeddings import MissingApiKeyError, ProviderError, QuotaExceededError

router = APIRouter(prefix="/analytics", tags=["analytics"])
settings = get_settings()


@router.post("/evaluate", response_model=AnalyticsOut, status_code=status.HTTP_201_CREATED)
def evaluate_answer(
    body: EvaluateRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AnalyticsOut:
    if not body.reference_answer.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reference answer is required.")

    message = db.get(Message, body.message_id)
    if message is None or message.role != "assistant":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assistant message not found.")
    session = get_owned_session(db, user, message.session_id)  # enforces ownership

    question_msg = crud.preceding_user_message(db, session.id, message.created_at)
    question = question_msg.content if question_msg else ""

    try:
        contexts = (
            [d.page_content for d in vectorstore.search(question, session_id=session.id, k=settings.retrieval_top_k)]
            if question
            else []
        )
        scores = evaluation.evaluate_answer(
            question=question,
            answer=message.content,
            contexts=contexts,
            reference=body.reference_answer,
        )
    except MissingApiKeyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except QuotaExceededError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    row = crud.add_analytics_result(
        db,
        session.id,
        message.id,
        faithfulness=scores.faithfulness,
        answer_relevancy=scores.answer_relevancy,
        context_precision=scores.context_precision,
    )
    return AnalyticsOut.model_validate(row)


@router.get("/{session_id}", response_model=list[AnalyticsOut])
def get_analytics(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[AnalyticsOut]:
    get_owned_session(db, user, session_id)
    return [AnalyticsOut.model_validate(r) for r in crud.list_analytics(db, session_id)]
