"""Shared prompt contract for Phase 8B/8C/8D dataset construction and training.

This module is the single source of truth for the enterprise grounding prompt,
context-pack formatting, TRL conversational record builders, and citation
validation. Phase 8C (SFT/DPO training) and Phase 8D (evaluation) import these
helpers so every dataset and generation step obeys the same contract.

The refusal string must stay byte-for-byte identical to
``backend/app/rag/constants.py`` so held-out behaviour matches production.
"""

import re
from typing import Any

REFUSAL_STRING = "I do not have enough information in the provided documents to answer this query."

SYSTEM_PROMPT = (
    "You are a precise enterprise document assistant. Answer using only the numbered "
    "sources provided in the user message.\n"
    "Rules:\n"
    "1. Ground every answer strictly in the provided numbered sources; never use "
    "outside memory.\n"
    "2. Cite each factual claim inline as [Source N], matching the source numbers "
    "given.\n"
    "3. Do not extrapolate, merge distinct entities or rows, or blend separate "
    "documents.\n"
    f'4. If the decisive evidence is absent, reply with exactly: "{REFUSAL_STRING}" '
    "and no other text."
)

_CITATION_RE = re.compile(r"\[Source (\d+)\]")


def format_context_pack(chunks: list[dict[str, Any]]) -> str:
    """Render chunks as a deterministic, prefix-cache-friendly context block.

    Chunks are rendered in the order given (callers are responsible for a
    deterministic ordering) as ``[Source 1]`` through ``[Source K]``, each with a
    ``(Document: <doc_id>, Page: <page>)`` header (ADR-019).
    """
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        doc_id = chunk.get("doc_id", "unknown")
        page = chunk.get("page", "unknown")
        text = str(chunk.get("window_text", chunk.get("text", ""))).strip()
        blocks.append(f"[Source {index}] (Document: {doc_id}, Page: {page})\n{text}")
    return "\n\n".join(blocks)


def build_user_message(context_pack: str, question: str) -> str:
    """Place the context block first and the user query last (prefix-cache friendly)."""
    return f"{context_pack}\n\nUser Query: {question}"


def build_sft_record(
    *,
    question: str,
    answer: str,
    chunks: list[dict[str, Any]],
    doc_id: str | None = None,
    split: str = "train",
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a TRL conversational SFT record from a grounded question/answer pair."""
    context_pack = format_context_pack(chunks)
    user_message = build_user_message(context_pack, question)
    metadata: dict[str, Any] = {
        "doc_id": doc_id,
        "split": split,
        "num_sources": len(chunks),
        "chunk_ids": [chunk.get("chunk_id") for chunk in chunks],
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": answer},
        ],
        "metadata": metadata,
    }


def build_dpo_record(
    *,
    question: str,
    chosen_answer: str,
    rejected_answer: str,
    chunks: list[dict[str, Any]],
    doc_id: str | None = None,
    split: str = "train",
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a TRL conversational DPO preference record (chosen vs rejected)."""
    context_pack = format_context_pack(chunks)
    user_message = build_user_message(context_pack, question)
    metadata: dict[str, Any] = {
        "doc_id": doc_id,
        "split": split,
        "num_sources": len(chunks),
        "chunk_ids": [chunk.get("chunk_id") for chunk in chunks],
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "prompt": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "chosen": [{"role": "assistant", "content": chosen_answer}],
        "rejected": [{"role": "assistant", "content": rejected_answer}],
        "metadata": metadata,
    }


def extract_citation_indices(text: str) -> list[int]:
    """Return the ``[Source N]`` indices found in ``text``, in order of appearance."""
    return [int(match.group(1)) for match in _CITATION_RE.finditer(text)]


def validate_response_format(
    text: str,
    num_sources: int,
    expect_refusal: bool,
) -> tuple[bool, str]:
    """Validate a generated response against the shared prompt contract.

    Returns ``(ok, reason)``.
    """
    stripped = text.strip()

    if expect_refusal:
        if stripped == REFUSAL_STRING:
            return True, "refusal string returned verbatim"
        return False, "expected the verbatim refusal string"

    if stripped == REFUSAL_STRING:
        return False, "refusal returned but a grounded answer was expected"

    citations = extract_citation_indices(text)
    if not citations:
        return False, "no [Source N] citations found"

    out_of_range = sorted({idx for idx in citations if idx < 1 or idx > num_sources})
    if out_of_range:
        return False, f"citation indices out of range: {out_of_range}"

    return True, f"{len(citations)} citation(s) present and in range"
