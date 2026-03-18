"""Router-level tests for chat-first checkpoint state auto bootstrap."""

from unittest.mock import patch

import pytest

from src.education.schemas import ActorContext, CheckpointDecision
from src.gateway.routers.education_checkpoints import decide_checkpoint


class _FakeStore:
    def __init__(self):
        self.state = {
            "orgs": {},
            "projects": {},
            "runs": {},
            "templates": {},
            "resources": {},
            "student_tasks": {},
            "student_submissions": {},
            "run_signals": {},
            "audit_logs": [],
        }

    def read_state(self):
        return self.state

    def write_state(self, state):
        self.state = state

    def transaction(self, mutator):
        return mutator(self.state)

    def generate_id(self, prefix: str) -> str:
        return f"{prefix}_test"


@pytest.mark.anyio
async def test_decide_checkpoint_auto_bootstraps_run_when_missing():
    store = _FakeStore()
    actor = ActorContext(user_id="teacher-1", org_id="org-default", role="teacher")

    with patch("src.gateway.routers.education_checkpoints.get_education_store", return_value=store):
        result = await decide_checkpoint(
            run_id="thread-chat-run-1",
            payload=CheckpointDecision(
                checkpoint_id="cp1-task-confirmation",
                option="继续并锁定当前任务约束",
            ),
            actor=actor,
        )

    assert result.run.id == "thread-chat-run-1"
    assert result.run.project_id == "proj_chat_bootstrap"
    assert result.run.org_id == "org-default"
    assert "thread-chat-run-1" in store.state["runs"]
