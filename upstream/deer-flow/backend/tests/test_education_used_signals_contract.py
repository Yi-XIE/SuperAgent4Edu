"""Contract tests for run-level used_signals exposure in memory API."""

from unittest.mock import patch

import pytest

from src.gateway.routers.memory import EDUCATION_AGENT_NAME, get_memory


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
        "facts": [
            {
                "id": "fact_1",
                "category": "teacher_preference",
                "content": "偏好40分钟课时",
                "confidence": 0.9,
                "createdAt": "2026-03-16T00:00:00Z",
                "source": "thread_1",
            }
        ],
    }


@pytest.mark.anyio
async def test_memory_api_returns_used_signals_for_education_agent_with_run_id():
    memory_data = _base_memory()
    with (
        patch("src.gateway.routers.memory.get_memory_data", return_value=memory_data),
        patch(
            "src.gateway.routers.memory.record_used_signals",
            return_value=[
                {
                    "category": "teacher_preference",
                    "content": "偏好40分钟课时",
                    "confidence": 0.9,
                    "source": "memory_api",
                    "used_at": "2026-03-16T00:00:00Z",
                }
            ],
        ) as mocked_record,
    ):
        response = await get_memory(
            agent_name=EDUCATION_AGENT_NAME,
            run_id="run_used_signal_1",
        )

    assert response.education_signals is not None
    assert response.used_signals is not None
    assert response.used_signals[0].source == "memory_api"
    mocked_record.assert_called_once()


@pytest.mark.anyio
async def test_memory_api_non_education_agent_reads_existing_used_signals():
    memory_data = _base_memory()
    with (
        patch("src.gateway.routers.memory.get_memory_data", return_value=memory_data),
        patch(
            "src.gateway.routers.memory.get_used_signals",
            return_value=[
                {
                    "category": "team_template",
                    "content": "固定使用UbD模板",
                    "confidence": 0.8,
                    "source": "memory_injection",
                    "used_at": "2026-03-16T00:00:00Z",
                }
            ],
        ) as mocked_get_used,
    ):
        response = await get_memory(agent_name="generic-agent", run_id="run_2")

    assert response.education_signals is None
    assert response.used_signals is not None
    assert response.used_signals[0].category == "team_template"
    mocked_get_used.assert_called_once_with("run_2")
