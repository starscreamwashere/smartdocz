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
from app.services.embeddings import MissingApiKeyError, ProviderError, QuotaExceededError
from app.services.loaders import (
    DocumentParseError,
    UnsupportedFileTypeError,
    detect_file_type,
    load_youtube,
)
from app.services.rag import ingest_documents, ingest_file

router = APIRouter(tags=["files"])
settings = get_settings()

_SUPPORTED_HINT = "Supported: PDF, DOCX, TXT, CSV, JSON, and YouTube URLs."


def _resolve_session(db: Session, user, session_id: uuid.UUID | None, title: str):
    """Reuse the caller's session or open a fresh one titled after the source."""
    if session_id is not None:
        return get_owned_session(db, user, session_id)
    return create_session(db, user, title=title)


def _finalize(db: Session, record: UploadedFile, session_id: uuid.UUID, ingest) -> UploadResponse:
    """Run ingestion with consistent status transitions + error mapping."""
    try:
        chunks = ingest()
    except MissingApiKeyError as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except QuotaExceededError as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc
    except ProviderError as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except (UnsupportedFileTypeError, DocumentParseError) as exc:
        record.upload_status = "failed"
        db.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unable to process the source: {exc}",
        ) from exc

    record.upload_status = "embedded"
    db.commit()
    db.refresh(record)
    return UploadResponse(
        file=FileOut.model_validate(record),
        session_id=session_id,
        chunks_stored=chunks,
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile | None = File(None),
    youtube_url: Annotated[str | None, Form()] = None,
    session_id: Annotated[uuid.UUID | None, Form()] = None,
) -> UploadResponse:
    has_file = file is not None and file.filename
    if bool(has_file) == bool(youtube_url):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide exactly one of a file or a YouTube URL.",
        )

    # ---- YouTube transcript ----
    if youtube_url:
        title, docs = _load_youtube_or_400(youtube_url)
        session = _resolve_session(db, user, session_id, title)
        text = "\n".join(d.page_content for d in docs)
        storage_url = storage.save_upload(user.id, session.id, f"{title}.txt", text.encode("utf-8"))
        record = UploadedFile(
            user_id=user.id, session_id=session.id, filename=title,
            file_type="youtube_transcript", storage_url=storage_url,
            file_size_mb=round(len(text.encode()) / (1024 * 1024), 4),
            upload_status="processing",
        )
        db.add(record); db.commit(); db.refresh(record)
        return _finalize(
            db, record, session.id,
            lambda: ingest_documents(docs, user_id=user.id, session_id=session.id, file_id=record.id),
        )

    # ---- File upload ----
    assert file is not None
    file_type = detect_file_type(file.filename or "")
    if file_type is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file format. {_SUPPORTED_HINT}",
        )

    data = await file.read()
    size_mb = len(data) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the maximum allowed size of {settings.max_upload_mb:.0f} MB.",
        )

    session = _resolve_session(db, user, session_id, Path(file.filename or "Untitled").stem)
    storage_url = storage.save_upload(user.id, session.id, file.filename or "upload", data)
    record = UploadedFile(
        user_id=user.id, session_id=session.id, filename=file.filename or "upload",
        file_type=file_type, storage_url=storage_url,
        file_size_mb=round(size_mb, 4), upload_status="processing",
    )
    db.add(record); db.commit(); db.refresh(record)
    return _finalize(
        db, record, session.id,
        lambda: ingest_file(storage_url, file_type, user_id=user.id, session_id=session.id, file_id=record.id),
    )


def _load_youtube_or_400(url: str):
    """Fetch a transcript, mapping parse failures to 422 before any DB writes."""
    try:
        return load_youtube(url)
    except DocumentParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


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
