"""Chat APIs — scaffolded in Milestone 1, implemented in Milestone 2.

RAG question answering (retrieve → LLM → grounded answer) lands in M2.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser

router = APIRouter(tags=["chat"])

_NOT_YET = "Chat / RAG answering ships in Milestone 2."


@router.post("/chat")
def send_message(user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/messages/{session_id}")
def get_messages(session_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
