"""File APIs — scaffolded in Milestone 1, implemented in Milestone 2.

Upload + processing pipeline (loader → chunk → embed → vector store) lands in M2.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth import CurrentUser

router = APIRouter(tags=["files"])

_NOT_YET = "File upload + processing ships in Milestone 2."


@router.post("/upload")
def upload_file(user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/files/{file_id}")
def get_file(file_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.delete("/files/{file_id}")
def delete_file(file_id: str, user: CurrentUser):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
