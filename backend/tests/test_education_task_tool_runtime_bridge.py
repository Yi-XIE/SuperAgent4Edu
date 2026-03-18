"""File-level contracts for education runtime bridge in task tool."""

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_task_tool_contains_runtime_skip_bridge_logic():
    content = (
        _repo_root()
        / "backend"
        / "src"
        / "tools"
        / "builtins"
        / "task_tool.py"
    ).read_text(encoding="utf-8")
    assert "def _should_skip_education_subtask" in content
    assert "workflow template disabled stage" in content
    assert 'run.critic_policy == "manual_off"' in content
    assert 'run.critic_policy == "auto"' in content


def test_task_tool_contains_reviewer_critic_sync_bridge():
    content = (
        _repo_root()
        / "backend"
        / "src"
        / "tools"
        / "builtins"
        / "task_tool.py"
    ).read_text(encoding="utf-8")
    assert "def _sync_education_runtime_state" in content
    assert "reviewer-summary.json" in content
    assert "critic-summary.json" in content
    assert "reviewer summary synced to run state" in content
