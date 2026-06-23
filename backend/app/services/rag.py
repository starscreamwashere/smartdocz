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

from langchain_core.documents import Document

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
question using ONLY the provided document context. Use the conversation memory \
and recent turns to resolve references (e.g. what "it" refers to), but never \
invent facts that are not in the document context. If the context does not \
contain the answer, say you could not find it in the document. Be concise and \
cite page numbers where helpful."""

_NO_CONTEXT = "I could not find relevant information in the uploaded documents."


def _retrieval_query(question: str, history: list[tuple[str, str]] | None) -> str:
    """Enrich the vector-search query with recent user turns so follow-ups
    (pronouns, "compare it with…") retrieve the earlier subject too."""
    if not history:
        return question
    recent_user = [content for role, content in history if role == "user"][-2:]
    return " ".join([*recent_user, question]) if recent_user else question


def _format_history(history: list[tuple[str, str]] | None) -> str:
    if not history:
        return ""
    lines = "\n".join(f"{role}: {content}" for role, content in history)
    return f"\n=== Recent conversation ===\n{lines}\n"


def _format_memory(memory_summary: str | None) -> str:
    if not memory_summary:
        return ""
    return f"\n=== Conversation memory ===\n{memory_summary}\n"


def ingest_documents(
    docs: list[Document],
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    file_id: uuid.UUID,
) -> int:
    """Chunk → embed → store pre-loaded documents. Returns chunks stored."""
    chunks = chunk_documents(
        docs, user_id=user_id, session_id=session_id, file_id=file_id
    )
    return vectorstore.add_chunks(chunks, file_id=file_id)


def ingest_file(
    path: str,
    file_type: str,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    file_id: uuid.UUID,
) -> int:
    """Load a file → chunk → embed → store. Returns the number of chunks stored."""
    docs = load_document(path, file_type)
    return ingest_documents(docs, user_id=user_id, session_id=session_id, file_id=file_id)


def _build_prompt(
    question: str,
    contexts: list[str],
    history: list[tuple[str, str]] | None,
    memory_summary: str | None,
) -> str:
    joined = "\n\n".join(f"[Context {i + 1}]\n{c}" for i, c in enumerate(contexts))
    return (
        f"{_SYSTEM_PROMPT}\n"
        f"{_format_memory(memory_summary)}"
        f"{_format_history(history)}"
        f"\n=== Document context ===\n{joined}\n\n"
        f"=== Current question ===\n{question}\n\n=== Answer ==="
    )


def answer_question(
    question: str,
    *,
    session_id: uuid.UUID,
    history: list[tuple[str, str]] | None = None,
    memory_summary: str | None = None,
) -> Answer:
    """Retrieve top-K chunks (query enriched with recent turns) and generate a
    grounded answer, with conversation memory injected for reference resolution."""
    docs = vectorstore.search(
        _retrieval_query(question, history),
        session_id=session_id,
        k=settings.retrieval_top_k,
    )

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
    result = generate(_build_prompt(question, contexts, history, memory_summary))
    return Answer(text=result.text, sources=sources, has_context=True, llm=result)
