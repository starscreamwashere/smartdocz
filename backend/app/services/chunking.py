"""Chunking — split page documents into retrievable chunks with metadata.

Carries page_number through and assigns a document-wide chunk_index, matching
the Qdrant payload spec (Backend Schema §6): file_id, session_id, user_id,
chunk_index, page_number, chunk_text.
"""
from __future__ import annotations

import uuid

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

settings = get_settings()


def chunk_documents(
    docs: list[Document],
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    file_id: uuid.UUID,
) -> list[Document]:
    """Split page documents into chunks, stamping retrieval metadata on each."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    split = splitter.split_documents(docs)

    chunks: list[Document] = []
    for index, doc in enumerate(split):
        doc.metadata = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "file_id": str(file_id),
            "chunk_index": index,
            "page_number": int(doc.metadata.get("page_number", 0)),
        }
        chunks.append(doc)
    return chunks
