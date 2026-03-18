"""Tests for HITL memory behavior in education-course-studio flows."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agents.middlewares.memory_middleware import MemoryMiddleware


def _runtime(thread_id: str = "thread-education-1") -> SimpleNamespace:
    return SimpleNamespace(context={"thread_id": thread_id})


def test_clarification_interrupt_run_does_not_queue_memory_update():
    middleware = MemoryMiddleware(agent_name="education-course-studio")
    queue = MagicMock()

    state = {
        "messages": [
            HumanMessage(content="请帮我设计一节 AI 课程。"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "ask_clarification",
                        "args": {"question": "课时数是多少？"},
                    }
                ],
            ),
            ToolMessage(
                content="❓ 任务确认点：请确认本轮课程设计约束\n\n  1. 继续并锁定当前任务约束",
                tool_call_id="call-1",
                name="ask_clarification",
            ),
        ]
    }

    with (
        patch(
            "src.agents.middlewares.memory_middleware.get_memory_config",
            return_value=SimpleNamespace(enabled=True),
        ),
        patch("src.agents.middlewares.memory_middleware.get_memory_queue", return_value=queue),
    ):
        middleware.after_agent(state, _runtime())

    queue.add.assert_not_called()


def test_final_teacher_package_response_is_queued_for_memory_update():
    middleware = MemoryMiddleware(agent_name="education-course-studio")
    queue = MagicMock()

    state = {
        "messages": [
            HumanMessage(content="继续并锁定当前任务约束"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-2",
                        "name": "task",
                        "args": {"description": "[Reviewer] 课程质量评审"},
                    }
                ],
            ),
            ToolMessage(
                content="Task Succeeded. Result: reviewer summary completed",
                tool_call_id="call-2",
                name="task",
            ),
            AIMessage(content="Reviewer结论：有条件通过。已完成课程包，请审阅并确认最终草案。"),
        ]
    }

    with (
        patch(
            "src.agents.middlewares.memory_middleware.get_memory_config",
            return_value=SimpleNamespace(enabled=True),
        ),
        patch("src.agents.middlewares.memory_middleware.get_memory_queue", return_value=queue),
    ):
        middleware.after_agent(state, _runtime())

    queue.add.assert_called_once()
    kwargs = queue.add.call_args.kwargs
    assert kwargs["thread_id"] == "thread-education-1"
    assert kwargs["agent_name"] == "education-course-studio"
    assert [msg.type for msg in kwargs["messages"]] == ["human", "ai"]
    assert "Reviewer结论：有条件通过" in kwargs["messages"][1].content
