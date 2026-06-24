"""RAG answer-quality evaluation (Milestone 6).

Computes the three RAGAS metrics — Faithfulness, Answer Relevancy, Context
Precision — via a single LLM-as-judge call (quota-friendly) using the shared
Gemini client. Same metric definitions and targets as the TRD; not the RAGAS
library itself.

Targets (TRD §12): faithfulness ≥ 0.85, answer_relevancy ≥ 0.80,
context_precision ≥ 0.80.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.llm import generate

TARGETS = {"faithfulness": 0.85, "answer_relevancy": 0.80, "context_precision": 0.80}


@dataclass
class EvalScores:
    faithfulness: float
    answer_relevancy: float
    context_precision: float


_PROMPT = """You are a strict RAG answer-quality evaluator. Score the GENERATED \
ANSWER on three metrics, each a float from 0.0 to 1.0.

Definitions:
- faithfulness: the fraction of the generated answer's factual claims that are \
directly supported by the Retrieved Context. Penalize any claim not grounded in \
the context (hallucination). 1.0 = every claim is grounded.
- answer_relevancy: how directly and completely the generated answer addresses \
the Question (independent of factual correctness). 1.0 = fully on-point, no \
padding and no omissions.
- context_precision: the fraction of the Retrieved Context passages that are \
relevant/useful for answering the Question. 1.0 = every passage is relevant.

Use the Reference Answer only as a guide to what a correct, complete answer \
looks like. Be discerning; do not give 1.0 unless fully warranted.

Return ONLY a JSON object, no prose:
{{"faithfulness": <float>, "answer_relevancy": <float>, "context_precision": <float>}}

=== Question ===
{question}

=== Retrieved Context ===
{contexts}

=== Generated Answer ===
{answer}

=== Reference Answer ===
{reference}

JSON:"""


def _clamp(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _parse_scores(text: str) -> EvalScores:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    return EvalScores(
        faithfulness=_clamp(data.get("faithfulness")),
        answer_relevancy=_clamp(data.get("answer_relevancy")),
        context_precision=_clamp(data.get("context_precision")),
    )


def evaluate_answer(
    *, question: str, answer: str, contexts: list[str], reference: str
) -> EvalScores:
    joined = "\n\n".join(f"[Context {i + 1}] {c}" for i, c in enumerate(contexts)) or "(no context retrieved)"
    prompt = _PROMPT.format(
        question=question or "(no question recorded)",
        contexts=joined,
        answer=answer,
        reference=reference,
    )
    return _parse_scores(generate(prompt).text)
