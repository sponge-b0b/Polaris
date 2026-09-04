from __future__ import annotations

import pytest

from domain.llm import (
    ReasoningTraceViolationError,
    reject_reasoning_trace,
    sanitize_reasoning_trace_payload,
    sanitize_reasoning_trace_text,
)


def test_sanitizer_strips_complete_thinking_tags_from_publishable_text() -> None:
    result = sanitize_reasoning_trace_text(
        "<think>inspect private chain of thought</think>\nPublic answer."
    )

    assert result.detected is True
    assert result.stripped is True
    assert result.unsafe is False
    assert result.text == "Public answer."
    assert "private chain of thought" not in result.text


def test_sanitizer_strips_reasoning_fences_without_text_overlap() -> None:
    result = sanitize_reasoning_trace_text(
        "```reasoning\nhidden scratchpad\n```\nFinal recommendation is neutral."
    )

    assert result.detected is True
    assert result.stripped is True
    assert result.unsafe is False
    assert result.text == "Final recommendation is neutral."
    assert "hidden scratchpad" not in result.text


def test_sanitizer_strips_prefixed_reasoning_before_final_answer() -> None:
    result = sanitize_reasoning_trace_text(
        "Chain of thought: inspect hidden calculations.\n"
        "Final answer: Maintain the current allocation."
    )

    assert result.detected is True
    assert result.stripped is True
    assert result.unsafe is False
    assert result.text == "Maintain the current allocation."
    assert "hidden calculations" not in result.text


def test_reject_reasoning_trace_fails_closed_on_unclosed_marker() -> None:
    with pytest.raises(ReasoningTraceViolationError) as exc_info:
        reject_reasoning_trace(
            "<think>hidden reasoning with no closing tag", boundary_name="json"
        )

    assert "json" in str(exc_info.value)
    assert "hidden reasoning" not in str(exc_info.value)


def test_payload_sanitizer_excludes_explicit_reasoning_keys() -> None:
    payload = {
        "summary": "Visible model summary.",
        "chain_of_thought": "private deliberation",
        "nested": {
            "scratchpad": "hidden notes",
            "evidence": "public evidence",
        },
    }

    sanitized = sanitize_reasoning_trace_payload(
        payload,
        boundary_name="typed_contract",
    )

    assert sanitized == {
        "summary": "Visible model summary.",
        "nested": {"evidence": "public evidence"},
    }


def test_payload_sanitizer_strips_delimited_reasoning_from_nested_text() -> None:
    payload = {
        "summary": "<think>private deliberation</think>\nVisible summary.",
        "items": [
            "```reasoning\nhidden scratchpad\n```\nVisible item.",
        ],
    }

    sanitized = sanitize_reasoning_trace_payload(
        payload,
        boundary_name="durable_record",
    )

    assert sanitized == {
        "summary": "Visible summary.",
        "items": ("Visible item.",),
    }


def test_payload_sanitizer_fails_closed_without_leaking_unsafe_reasoning() -> None:
    with pytest.raises(ReasoningTraceViolationError) as exc_info:
        sanitize_reasoning_trace_payload(
            {"summary": "<think>private unsafe deliberation"},
            boundary_name="curated_record",
        )

    message = str(exc_info.value)
    assert "curated_record.summary" in message
    assert "private unsafe deliberation" not in message
