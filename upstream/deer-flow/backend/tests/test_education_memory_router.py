"""Tests for education-specific memory API response behavior."""

from unittest.mock import patch

import pytest

from src.gateway.routers.memory import (
    EDUCATION_AGENT_NAME,
    _build_education_signals,
    get_memory,
)


def _base_memory() -> dict:
    return {
        "version": "1.0",
        "lastUpdated": "2026-03-16T00:00:00Z",
        "user": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "history": {
            "recentMonths": {"summary": "", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }


def _fact(
    *,
    category: str,
    content: str,
    confidence: float,
    fact_id: str,
) -> dict:
    return {
        "id": fact_id,
        "content": content,
        "category": category,
        "confidence": confidence,
        "createdAt": "2026-03-16T00:00:00Z",
        "source": "thread-education",
    }


def test_build_education_signals_filters_categories_and_sorts():
    memory_data = _base_memory()
    memory_data["facts"] = [
        _fact(category="team_template", content="Use weekly reflection", confidence=0.72, fact_id="fact-1"),
        _fact(category="context", content="Ignore me", confidence=0.99, fact_id="fact-2"),
        _fact(category="teacher_preference", content="Prefer 40-minute sessions", confidence=0.91, fact_id="fact-3"),
        _fact(category="learning_kit_preference", content="Low-cost recyclable kits", confidence=0.88, fact_id="fact-4"),
        _fact(category="course_continuity", content="Continue sensor unit", confidence=0.79, fact_id="fact-5"),
    ]

    signals = _build_education_signals(memory_data)

    assert [signal.category for signal in signals] == [
        "teacher_preference",
        "learning_kit_preference",
        "course_continuity",
        "team_template",
    ]
    assert signals[0].content == "Prefer 40-minute sessions"


@pytest.mark.anyio
async def test_memory_endpoint_without_agent_name_keeps_global_response_shape():
    memory_data = _base_memory()
    memory_data["facts"] = [
        _fact(category="teacher_preference", content="foo", confidence=0.9, fact_id="fact-6")
    ]

    with patch("src.gateway.routers.memory.get_memory_data", return_value=memory_data) as mock_mem:
        result = await get_memory()

    mock_mem.assert_called_once_with(None)
    assert result.version == "1.0"
    assert result.education_signals is None


@pytest.mark.anyio
async def test_memory_endpoint_with_education_agent_returns_education_signals():
    memory_data = _base_memory()
    memory_data["facts"] = [
        _fact(
            category="teacher_preference",
            content="Prefer concise teacher notes",
            confidence=0.95,
            fact_id="fact-7",
        ),
        _fact(
            category="learning_kit_preference",
            content="Use safe low-voltage parts",
            confidence=0.9,
            fact_id="fact-8",
        ),
        _fact(
            category="context",
            content="Not education signal",
            confidence=1.0,
            fact_id="fact-9",
        ),
    ]

    with patch("src.gateway.routers.memory.get_memory_data", return_value=memory_data) as mock_mem:
        result = await get_memory(agent_name=EDUCATION_AGENT_NAME)

    mock_mem.assert_called_once_with(EDUCATION_AGENT_NAME)
    assert result.education_signals is not None
    assert len(result.education_signals) == 2
    assert result.education_signals[0].category == "teacher_preference"


@pytest.mark.anyio
async def test_memory_endpoint_with_non_education_agent_has_no_education_signals():
    memory_data = _base_memory()
    memory_data["facts"] = [
        _fact(category="teacher_preference", content="foo", confidence=0.9, fact_id="fact-10")
    ]

    with patch("src.gateway.routers.memory.get_memory_data", return_value=memory_data) as mock_mem:
        result = await get_memory(agent_name="generic-agent")

    mock_mem.assert_called_once_with("generic-agent")
    assert result.education_signals is None
