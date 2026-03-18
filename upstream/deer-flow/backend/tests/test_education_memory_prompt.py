"""Tests for education-course-studio memory customization."""

from src.agents.memory.prompt import (
    EDUCATION_AGENT_NAME,
    format_memory_for_injection,
    get_memory_update_prompt,
)


def test_education_agent_uses_specialized_memory_prompt():
    prompt = get_memory_update_prompt(EDUCATION_AGENT_NAME)

    assert "teacher_preference" in prompt
    assert "course_continuity" in prompt
    assert "learning_kit_preference" in prompt
    assert "team_template" in prompt


def test_other_agents_keep_default_memory_prompt():
    prompt = get_memory_update_prompt("generic-agent")

    assert "teacher_preference" not in prompt
    assert "course_continuity" not in prompt


def test_education_agent_injection_includes_education_signals():
    memory_data = {
        "user": {
            "workContext": {"summary": "Designing elementary AI courses.", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "Preparing a UbD/PBL unit.", "updatedAt": ""},
        },
        "history": {
            "recentMonths": {"summary": "Recently built several project-based science lessons.", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {"summary": "", "updatedAt": ""},
        },
        "facts": [
            {
                "content": "Teacher prefers 40-minute sessions and concise teacher notes.",
                "category": "teacher_preference",
                "confidence": 0.95,
                "createdAt": "2026-03-14T00:00:00Z",
            },
            {
                "content": "The team reuses a weekly demo-reflection template for science units.",
                "category": "team_template",
                "confidence": 0.82,
                "createdAt": "2026-03-13T00:00:00Z",
            },
        ],
    }

    injected = format_memory_for_injection(memory_data, agent_name=EDUCATION_AGENT_NAME)

    assert "Education Signals:" in injected
    assert "Teacher Preference" in injected
    assert "Team Template" in injected


def test_non_education_agent_does_not_include_education_signals():
    memory_data = {
        "user": {},
        "history": {},
        "facts": [
            {
                "content": "Teacher prefers concise teacher notes.",
                "category": "teacher_preference",
                "confidence": 0.95,
                "createdAt": "2026-03-14T00:00:00Z",
            }
        ],
    }

    injected = format_memory_for_injection(memory_data, agent_name="generic-agent")

    assert "Education Signals:" not in injected
