"""LLM client — Gemini (Google AI Studio).

Milestone 2 uses Gemini directly. Milestone 7 introduces provider routing
(Gemini → Claude fallback) and LangGraph orchestration; this module is the
single seam where that lands.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings
from app.services.embeddings import MissingApiKeyError, ProviderError


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int


@lru_cache
def _client() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise MissingApiKeyError(
            "GOOGLE_API_KEY is not configured; cannot call the LLM."
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )


def generate(prompt: str) -> LLMResult:
    settings = get_settings()
    started = time.perf_counter()
    try:
        response = _client().invoke(prompt)
    except MissingApiKeyError:
        raise
    except Exception as exc:  # provider/network failure during generation
        raise ProviderError(f"Generation failed: {exc}") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)
    text = response.content if isinstance(response.content, str) else str(response.content)
    return LLMResult(
        text=text.strip(),
        provider="gemini",
        model=settings.gemini_model,
        latency_ms=latency_ms,
    )
