"""LLM client — provider-agnostic generation with fallback (Milestone 7).

Routing (TRD §9-10):

    Question → Model Router → primary provider → (on failure) fallback provider

Primary is chosen by LLM_PROVIDER (gemini|claude); the other provider is the
fallback when its API key is configured. A primary failure — including an
exhausted free-tier quota — automatically retries on the fallback, so the system
recovers from provider outages on its own. Each call reports the provider that
actually answered plus token usage and an estimated cost for model_runs.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import Settings, get_settings
from app.services.embeddings import MissingApiKeyError, ProviderError, retry_on_quota

logger = logging.getLogger("smartdocz")

# Approximate USD pricing per 1M tokens (input, output) for cost estimation.
_PRICING: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.0-flash": (0.10, 0.40),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
}


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int
    tokens_used: int | None = None
    estimated_cost: float | None = None


@lru_cache
def _gemini_client() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise MissingApiKeyError("GOOGLE_API_KEY is not configured.")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    )


@lru_cache
def _claude_client():
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not configured.")
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.anthropic_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.2,
        max_tokens=1024,
    )


def _model_name(provider: str, settings: Settings) -> str:
    return settings.gemini_model if provider == "gemini" else settings.anthropic_model


def _estimate_cost(model: str, usage: dict) -> float | None:
    price = _PRICING.get(model)
    if not price or not usage:
        return None
    price_in, price_out = price
    cost = (usage.get("input_tokens", 0) * price_in + usage.get("output_tokens", 0) * price_out) / 1_000_000
    return round(cost, 6)


def _provider_available(provider: str, settings: Settings) -> bool:
    if provider == "gemini":
        return bool(settings.google_api_key)
    if provider == "claude":
        return bool(settings.anthropic_api_key)
    return False


def _invoke(provider: str, prompt: str, *, fail_fast: bool) -> LLMResult:
    client = _gemini_client() if provider == "gemini" else _claude_client()
    settings = get_settings()
    # When a fallback exists, don't burn time retrying a quota-limited primary —
    # fail fast so we hand off to the other provider quickly.
    attempts = 1 if fail_fast else 3
    started = time.perf_counter()
    try:
        response = retry_on_quota(lambda: client.invoke(prompt), attempts=attempts)
    except (ProviderError, MissingApiKeyError):
        raise  # QuotaExceededError (a ProviderError) included
    except Exception as exc:  # billing, bad model, network, etc.
        raise ProviderError(f"{provider} generation failed: {exc}") from exc
    latency_ms = int((time.perf_counter() - started) * 1000)

    usage = getattr(response, "usage_metadata", None) or {}
    text = response.content if isinstance(response.content, str) else str(response.content)
    model = _model_name(provider, settings)
    return LLMResult(
        text=text.strip(),
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        tokens_used=usage.get("total_tokens"),
        estimated_cost=_estimate_cost(model, usage),
    )


def generate(prompt: str) -> LLMResult:
    """Generate text, routing to the configured primary with automatic fallback."""
    settings = get_settings()
    primary = settings.llm_provider if settings.llm_provider in ("gemini", "claude") else "gemini"
    fallback = "claude" if primary == "gemini" else "gemini"
    order = [p for p in (primary, fallback) if _provider_available(p, settings)]

    if not order:
        raise MissingApiKeyError(
            "No LLM provider configured. Set GOOGLE_API_KEY and/or ANTHROPIC_API_KEY."
        )

    has_fallback = len(order) > 1
    last_exc: Exception | None = None
    for index, provider in enumerate(order):
        is_primary = index == 0
        try:
            result = _invoke(provider, prompt, fail_fast=is_primary and has_fallback)
            if not is_primary:
                logger.warning("Recovered via fallback provider '%s'.", provider)
            return result
        except (ProviderError, MissingApiKeyError) as exc:  # quota included
            last_exc = exc
            remaining = index + 1 < len(order)
            logger.warning(
                "Provider '%s' failed (%s); %s",
                provider,
                type(exc).__name__,
                "falling back" if remaining else "no fallback available",
            )
    assert last_exc is not None
    raise last_exc
