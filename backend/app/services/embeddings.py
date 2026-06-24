"""Gemini embeddings (Google AI Studio), with quota-aware retries.

Embedding model is configured via EMBEDDING_MODEL (default gemini-embedding-001).
The free tier caps embed requests per minute, so we retry on 429/RESOURCE_EXHAUSTED
honoring Google's suggested retryDelay, and surface a clean QuotaExceededError when
the budget is still exhausted.

Lazily constructed so the app can boot without GOOGLE_API_KEY.
"""
from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from typing import Callable, TypeVar

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import get_settings

logger = logging.getLogger("smartdocz")

T = TypeVar("T")
_QUOTA_MARKERS = ("RESOURCE_EXHAUSTED", "429")
_MAX_ATTEMPTS = 3
_RETRY_CAP_SECONDS = 45.0


class MissingApiKeyError(RuntimeError):
    """Raised when an LLM/embedding call is attempted without GOOGLE_API_KEY."""


class ProviderError(RuntimeError):
    """Raised when the LLM/embedding provider returns an error (bad model, network)."""


class QuotaExceededError(ProviderError):
    """Raised when the provider's rate/quota limit is still exhausted after retries."""


def _is_quota_error(exc: Exception) -> bool:
    return any(marker in str(exc) for marker in _QUOTA_MARKERS)


def _retry_delay_seconds(exc: Exception, default: float = 8.0) -> float:
    text = str(exc)
    match = re.search(r"retry(?:Delay)?['\"]?:?\s*['\"]?(\d+(?:\.\d+)?)\s*s", text) or re.search(
        r"retry in (\d+(?:\.\d+)?)", text
    )
    seconds = float(match.group(1)) + 1.0 if match else default
    return min(seconds, _RETRY_CAP_SECONDS)


def retry_on_quota(fn: Callable[[], T], *, attempts: int = _MAX_ATTEMPTS) -> T:
    """Run fn, retrying on quota errors with the server-suggested delay."""
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — re-raised below
            if not _is_quota_error(exc):
                raise
            last = exc
            if attempt == attempts - 1:
                break
            delay = _retry_delay_seconds(exc)
            logger.warning("Gemini quota hit; retrying in %.1fs (attempt %d)", delay, attempt + 1)
            time.sleep(delay)
    raise QuotaExceededError(
        "Gemini free-tier rate limit reached (embeddings: ~100 requests/min). "
        "Please wait about a minute and try again."
    ) from last


class RetryingEmbeddings(Embeddings):
    """Wraps a LangChain Embeddings impl with quota-aware retries."""

    def __init__(self, inner: Embeddings) -> None:
        self._inner = inner

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return retry_on_quota(lambda: self._inner.embed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        return retry_on_quota(lambda: self._inner.embed_query(text))


@lru_cache
def get_embeddings() -> Embeddings:
    settings = get_settings()
    if not settings.google_api_key:
        raise MissingApiKeyError(
            "GOOGLE_API_KEY is not configured; cannot generate embeddings."
        )
    inner = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
    return RetryingEmbeddings(inner)
