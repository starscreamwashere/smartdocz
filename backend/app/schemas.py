"""Pydantic response/request schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_user_id: str
    email: str | None
    full_name: str | None
    created_at: datetime
    updated_at: datetime


class HealthOut(BaseModel):
    status: str
    service: str = "smartdocz-backend"


# ---- Sessions ----
class SessionCreate(BaseModel):
    title: str | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


class SessionSummary(SessionOut):
    """Session metadata plus lightweight counts for the history sidebar."""

    message_count: int
    file_count: int


# ---- Files ----
class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    filename: str
    file_type: str
    file_size_mb: float | None
    upload_status: str
    created_at: datetime


class UploadResponse(BaseModel):
    file: FileOut
    session_id: uuid.UUID
    chunks_stored: int


# ---- Chat ----
class ChatRequest(BaseModel):
    session_id: uuid.UUID
    message: str


class SourceOut(BaseModel):
    page_number: int
    chunk_index: int
    snippet: str


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    sources: list[SourceOut]
    has_context: bool
    model_provider: str
    model: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    model_provider: str | None
    created_at: datetime


# ---- Analytics ----
class EvaluateRequest(BaseModel):
    message_id: uuid.UUID
    reference_answer: str


class AnalyticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    created_at: datetime
