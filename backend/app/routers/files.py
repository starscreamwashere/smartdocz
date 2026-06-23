"""File APIs — Milestone 2: PDF upload + RAG ingestion.

Pipeline: validate → save raw file → record metadata → load → chunk → embed →
store in Chroma. Multi-format (DOCX/TXT/CSV/JSON/YouTube) arrives in Milestone 4.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.config import get_settings
from app.crud import create_session, get_owned_session
from app.database import get_db
from app.models import UploadedFile
from app.schemas import FileOut, UploadResponse
from app.services import storage
from app.services.embeddings import MissingApiKeyError, ProviderError
from app.services.loaders import DocumentParseError, UnsupportedFileTypeError
from app.services.rag import ingest_file

router = APIRouter(tags=["files"])
settings = get_settings()

# Milestone 2 accepts PDF only.
_M2_TYPES = {".pdf": "pdf"}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    session_id: Annotated[uuid.UUID | None, Form()] = None,
) -> UploadResponse:
    ext = Path(file.filename or "").suffix.lower()
    file_type = _M2_TYPES.get(ext)
    if file_type is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Unsupported file format. Only PDF is supported at this stage "
            "(DOCX, TXT, CSV, JSON, and YouTube arrive in Milestone 4).",
        )

    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the maximum allowed size of {settings.max_upload_mb:.0f} MB.",
        )

    # Resolve the session: reuse the caller's, or open a fresh one named after the file.
    if session_id is not None:
        session = get_owned_session(db, user, session_id)
    else:
        session = create_session(db, user, title=Path(file.filename or "Untitled").stem)

    storage_url = storage.save_upload(user.id, session.id, file.filename or "upload.pdf", data)

    record = UploadedFile(
        user_id=user.id,
        session_id=session.id,
        filename=file.filename or "upload.pdf",
        file_type=file_type,
        storage_url=storage_url,
        file_size_mb=round(size_mb, 4),
        upload_status="processing",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Ingest synchronously (TRD target: < 30s average).
    try:
        chunks = ingest_file(
            storage_url, file_type,
            user_id=user.id, session_id=session.id, file_id=record.id,
        )
    except MissingApiKeyError as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except ProviderError as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except (UnsupportedFileTypeError, DocumentParseError) as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unable to process the uploaded file: {exc}",
        ) from exc

    record.upload_status = "embedded"
    db.commit()
    db.refresh(record)

    return UploadResponse(
        file=FileOut.model_validate(record),
        session_id=session.id,
        chunks_stored=chunks,
    )


@router.get("/files/{file_id}", response_model=FileOut)
def get_file(file_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> FileOut:
    record = db.get(UploadedFile, file_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")
    return FileOut.model_validate(record)


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> None:
    record = db.get(UploadedFile, file_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found.")
    from app.services import vectorstore

    vectorstore.delete_file(record.id)
    db.delete(record)
    db.commit()
