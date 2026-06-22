"""Analytics APIs — scaffolded in Milestone 1, implemented in Milestone 6.

RAGAS evaluation (faithfulness, answer relevancy, context precision) lands in M6.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser

router = APIRouter(prefix="/analytics", tags=["analytics"])

_NOT_YET = "RAGAS analytics ships in Milestone 6."


@router.post("/evaluate")
def evaluate_answer(user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/{session_id}")
def get_analytics(session_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
