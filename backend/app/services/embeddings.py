"""Gemini embeddings (Google AI Studio).

Embedding model is configured via EMBEDDING_MODEL (default text-embedding-004).
Lazily constructed so the app can boot without GOOGLE_API_KEY; only embedding
operations require it.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import get_settings


class MissingApiKeyError(RuntimeError):
    """Raised when an LLM/embedding call is attempted without GOOGLE_API_KEY."""


class ProviderError(RuntimeError):
    """Raised when the LLM/embedding provider returns an error (e.g. bad model,
    quota, network)."""


@lru_cache
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    if not settings.google_api_key:
        raise MissingApiKeyError(
            "GOOGLE_API_KEY is not configured; cannot generate embeddings."
        )
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
