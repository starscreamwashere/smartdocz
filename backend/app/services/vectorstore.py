"""Vector store wrapper — Chroma (dev).

Stores one record per chunk with the Backend Schema §6 payload as metadata
(user_id, session_id, file_id, chunk_index, page_number) and the chunk text as
the document body. Retrieval is always filtered by session_id so a query only
ever sees the current session's documents (session isolation).

The interface (add_chunks / search) is deliberately small so Milestone 8 can
swap Chroma for Qdrant without touching the RAG logic.
"""
from __future__ import annotations

import uuid
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.services.embeddings import (
    MissingApiKeyError,
    ProviderError,
    QuotaExceededError,
    get_embeddings,
)


@lru_cache
def _store() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def add_chunks(chunks: list[Document], *, file_id: uuid.UUID) -> int:
    """Embed and store chunks. Returns the number stored."""
    if not chunks:
        return 0
    ids = [f"{file_id}_{c.metadata['chunk_index']}" for c in chunks]
    try:
        _store().add_documents(documents=chunks, ids=ids)
    except (MissingApiKeyError, QuotaExceededError):
        raise
    except Exception as exc:  # provider/network failure during embedding
        raise ProviderError(f"Embedding failed: {exc}") from exc
    return len(chunks)


def search(query: str, *, session_id: uuid.UUID, k: int) -> list[Document]:
    """Return the top-k chunks for a query within a session."""
    try:
        return _store().similarity_search(
            query, k=k, filter={"session_id": str(session_id)}
        )
    except (MissingApiKeyError, QuotaExceededError):
        raise
    except Exception as exc:
        raise ProviderError(f"Retrieval failed: {exc}") from exc


def delete_file(file_id: uuid.UUID) -> None:
    """Remove all chunks belonging to a file."""
    _store().delete(where={"file_id": str(file_id)})


def delete_session(session_id: uuid.UUID) -> None:
    """Remove all chunks belonging to a session."""
    _store().delete(where={"session_id": str(session_id)})
