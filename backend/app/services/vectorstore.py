"""Vector store wrapper — Chroma (dev) or Qdrant (prod).

Stores one record per chunk with the Backend Schema §6 payload (user_id,
session_id, file_id, chunk_index, page_number) plus the chunk text. Retrieval is
always filtered by session_id (session isolation).

The backend is chosen by configuration: if QDRANT_URL is set we use Qdrant
(production), otherwise Chroma (local development). The public interface
(add_chunks / search / delete_file / delete_session) is identical for both, so
the RAG layer is unaffected by the swap.
"""
from __future__ import annotations

import uuid
from functools import lru_cache

from langchain_core.documents import Document

from app.config import get_settings
from app.services.embeddings import (
    MissingApiKeyError,
    ProviderError,
    QuotaExceededError,
    get_embeddings,
)

# Deterministic namespace so a chunk always maps to the same Qdrant point id.
_POINT_NAMESPACE = uuid.UUID("5f4d3c2b-1a09-4e8d-9c7b-6a5f4e3d2c1b")


def _use_qdrant() -> bool:
    return bool(get_settings().qdrant_url)


# --------------------------------------------------------------------------- #
# Chroma (development)
# --------------------------------------------------------------------------- #
@lru_cache
def _chroma():
    from langchain_chroma import Chroma

    settings = get_settings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


# --------------------------------------------------------------------------- #
# Qdrant (production)
# --------------------------------------------------------------------------- #
@lru_cache
def _qdrant():
    """Return a (client, collection_name) tuple, creating the collection once."""
    from qdrant_client import QdrantClient, models

    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    collection = settings.chroma_collection

    if not client.collection_exists(collection):
        # Probe the embedding dimension once (varies by model).
        dim = len(get_embeddings().embed_query("dimension probe"))
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
    return client, collection


def _qdrant_filter(**equals: str):
    from qdrant_client import models

    return models.Filter(
        must=[
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in equals.items()
        ]
    )


# --------------------------------------------------------------------------- #
# Public interface
# --------------------------------------------------------------------------- #
def add_chunks(chunks: list[Document], *, file_id: uuid.UUID) -> int:
    """Embed and store chunks. Returns the number stored."""
    if not chunks:
        return 0
    try:
        if _use_qdrant():
            from qdrant_client import models

            client, collection = _qdrant()
            vectors = get_embeddings().embed_documents([c.page_content for c in chunks])
            points = [
                models.PointStruct(
                    id=str(uuid.uuid5(_POINT_NAMESPACE, f"{file_id}_{c.metadata['chunk_index']}")),
                    vector=vector,
                    payload={**c.metadata, "page_content": c.page_content},
                )
                for c, vector in zip(chunks, vectors)
            ]
            client.upsert(collection_name=collection, points=points)
        else:
            ids = [f"{file_id}_{c.metadata['chunk_index']}" for c in chunks]
            _chroma().add_documents(documents=chunks, ids=ids)
    except (MissingApiKeyError, QuotaExceededError):
        raise
    except Exception as exc:  # provider/network failure during embedding/store
        raise ProviderError(f"Embedding failed: {exc}") from exc
    return len(chunks)


def search(query: str, *, session_id: uuid.UUID, k: int) -> list[Document]:
    """Return the top-k chunks for a query within a session."""
    try:
        if _use_qdrant():
            client, collection = _qdrant()
            vector = get_embeddings().embed_query(query)
            hits = client.query_points(
                collection_name=collection,
                query=vector,
                query_filter=_qdrant_filter(session_id=str(session_id)),
                limit=k,
            ).points
            return [
                Document(
                    page_content=h.payload.get("page_content", ""),
                    metadata={key: val for key, val in h.payload.items() if key != "page_content"},
                )
                for h in hits
            ]
        return _chroma().similarity_search(query, k=k, filter={"session_id": str(session_id)})
    except (MissingApiKeyError, QuotaExceededError):
        raise
    except Exception as exc:
        raise ProviderError(f"Retrieval failed: {exc}") from exc


def _qdrant_delete(**equals: str) -> None:
    from qdrant_client import models

    client, collection = _qdrant()
    client.delete(
        collection_name=collection,
        points_selector=models.FilterSelector(filter=_qdrant_filter(**equals)),
    )


def delete_file(file_id: uuid.UUID) -> None:
    """Remove all chunks belonging to a file."""
    if _use_qdrant():
        _qdrant_delete(file_id=str(file_id))
    else:
        _chroma().delete(where={"file_id": str(file_id)})


def delete_session(session_id: uuid.UUID) -> None:
    """Remove all chunks belonging to a session."""
    if _use_qdrant():
        _qdrant_delete(session_id=str(session_id))
    else:
        _chroma().delete(where={"session_id": str(session_id)})
