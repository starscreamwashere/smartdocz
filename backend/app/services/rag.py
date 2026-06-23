"""RAG orchestration.

Two flows from the TRD §8:

  Ingest:  Upload → Loader → Chunk → Embed → Vector Store
  Answer:  Question → Embed → Vector Search → Top-K → LLM → Answer

In Milestone 7 this orchestration moves into LangGraph; for now it is a plain
function so the slice stays easy to follow.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.config import get_settings
from app.services import vectorstore
from app.services.chunking import chunk_documents
from app.services.llm import LLMResult, generate
from app.services.loaders import load_document

settings = get_settings()


@dataclass
class Source:
    page_number: int
    chunk_index: int
    snippet: str


@dataclass
class Answer:
    text: str
    sources: list[Source]
    has_context: bool
    llm: LLMResult


_SYSTEM_PROMPT = """You are SmartDocZ, a document assistant. Answer the user's \
question using ONLY the provided context from their uploaded document. \
If the context does not contain the answer, say you could not find it in the \
document — do not invent facts. Be concise and cite page numbers where helpful."""

_NO_CONTEXT = "I could not find relevant information in the uploaded documents."


def ingest_file(
    path: str,
    file_type: str,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    file_id: uuid.UUID,
) -> int:
    """Load → chunk → embed → store. Returns the number of chunks stored."""
    docs = load_document(path, file_type)
    chunks = chunk_documents(
        docs, user_id=user_id, session_id=session_id, file_id=file_id
    )
    return vectorstore.add_chunks(chunks, file_id=file_id)


def _build_prompt(question: str, contexts: list[str]) -> str:
    joined = "\n\n".join(f"[Context {i + 1}]\n{c}" for i, c in enumerate(contexts))
    return (
        f"{_SYSTEM_PROMPT}\n\n=== Document context ===\n{joined}\n\n"
        f"=== Question ===\n{question}\n\n=== Answer ==="
    )


def answer_question(question: str, *, session_id: uuid.UUID) -> Answer:
    """Retrieve top-K chunks for the session and generate a grounded answer."""
    docs = vectorstore.search(question, session_id=session_id, k=settings.retrieval_top_k)

    if not docs:
        # No retrieval hits → don't call the LLM; return the documented empty state.
        result = LLMResult(text=_NO_CONTEXT, provider="gemini", model=settings.gemini_model, latency_ms=0)
        return Answer(text=_NO_CONTEXT, sources=[], has_context=False, llm=result)

    contexts = [d.page_content for d in docs]
    sources = [
        Source(
            page_number=int(d.metadata.get("page_number", 0)),
            chunk_index=int(d.metadata.get("chunk_index", 0)),
            snippet=d.page_content[:240],
        )
        for d in docs
    ]
    result = generate(_build_prompt(question, contexts))
    return Answer(text=result.text, sources=sources, has_context=True, llm=result)
