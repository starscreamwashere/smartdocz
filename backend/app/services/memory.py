"""Conversation memory (Milestone 5).

Memory Flow (Backend Schema / Implementation Plan M5):

    Conversation → Summarization → Memory Summary → Future Context

A compact rolling summary of a session is generated periodically and stored in
`memory_summaries`. On each new question we inject the latest summary plus the
most recent raw turns, so follow-ups that rely on earlier context (e.g.
"compare it with chapter 5") resolve correctly while keeping token use low.
"""
from __future__ import annotations

# Regenerate the rolling summary every N messages (≈ every 3 exchanges).
SUMMARY_EVERY_N_MESSAGES = 6
# How many recent raw messages to inject verbatim alongside the summary.
RECENT_HISTORY_LIMIT = 6

_SUMMARY_PROMPT = """You maintain a running memory of a conversation between a \
user and a document assistant. Update the memory into 3-6 concise sentences that \
capture: the topics discussed, key facts established from the document(s), and any \
references the user made (chapters, sections, entities). Preserve antecedents so \
pronouns like "it"/"that" can be resolved later. Do not invent information.

{prior}Conversation so far:
{conversation}

Updated memory:"""


def should_update_summary(message_count: int) -> bool:
    return message_count >= SUMMARY_EVERY_N_MESSAGES and message_count % SUMMARY_EVERY_N_MESSAGES == 0


def summarize_conversation(
    turns: list[tuple[str, str]], prior_summary: str | None = None
) -> str:
    """Produce an updated rolling summary from (role, content) turns.

    Imported lazily-friendly: uses the shared Gemini client (with quota retries).
    """
    from app.services.llm import generate

    conversation = "\n".join(f"{role}: {content}" for role, content in turns)
    prior = f"Existing memory:\n{prior_summary}\n\n" if prior_summary else ""
    prompt = _SUMMARY_PROMPT.format(prior=prior, conversation=conversation)
    return generate(prompt).text
