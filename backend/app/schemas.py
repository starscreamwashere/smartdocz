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
