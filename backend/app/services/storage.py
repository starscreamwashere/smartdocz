"""Raw file storage.

Object Storage design (Backend Schema §7): /uploads/{user_id}/{session_id}/.
In development we persist to the local filesystem; the same layout maps cleanly
to S3/GCS later. Returns a storage URL/path recorded on uploaded_files.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def save_upload(
    user_id: uuid.UUID, session_id: uuid.UUID, filename: str, data: bytes
) -> str:
    """Persist raw bytes and return the storage path."""
    safe_name = Path(filename).name  # strip any path components
    dest_dir = Path(settings.upload_dir) / str(user_id) / str(session_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / safe_name
    dest.write_bytes(data)
    return str(dest)
