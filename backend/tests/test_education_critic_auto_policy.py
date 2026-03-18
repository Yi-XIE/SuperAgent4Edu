"""Critic auto-policy router contracts."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from src.education.schemas import (
    ActorContext,
    EducationRunState,
    ReviewerHardGateV2,
    ReviewerSummaryV2,
)
from src.gateway.routers.education_runs import set_reviewer_summary


class DummyStore:
    def __init__(self, state: dict):
        self.state = deepcopy(state)
        self._counter = 0

    def read_state(self):
        return self.state

    def transaction(self, mutator):
        return mutator(self.state)

    def generate_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _state(policy: str, details: str = "") -> dict:
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="评审测试",
        critic_enabled=False,
        critic_policy=policy,  # type: ignore[arg-type]
        details=details,
    )
    return {
        "orgs": {},
        "projects": {"proj_1": {"id": "proj_1", "org_id": "org_1", "name": "p", "owner_id": "u"}},
        "runs": {"run_1": run.model_dump()},
        "course_blueprints": {},
        "course_packages": {},
        "assets": {},
        "extractions": {},
        "feedback": {},
        "templates": {},
        "resources": {},
        "student_tasks": {},
        "student_submissions": {},
        "run_signals": {},
        "audit_logs": [],
    }


@pytest.mark.anyio
async def test_auto_policy_enables_critic_for_high_risk_borderline_reviewer():
    store = DummyStore(_state("auto", details="本轮含安全禁用约束，请严格复核"))
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    payload = ReviewerSummaryV2(
        verdict="有条件通过",
        hard_gates=[ReviewerHardGateV2(name="目标-证据一致性", status="pass", note="")],
        key_issues=["问题1", "问题2", "问题3"],
        rubric_scores=[],
        suggested_rerun_agents=["Package"],
        lead_note="边界场景",
    )
    with patch("src.gateway.routers.education_runs.get_education_store", return_value=store):
        updated = await set_reviewer_summary("run_1", payload, actor)

    assert updated.critic_policy == "auto"
    assert updated.critic_enabled is True
    assert updated.critic_activation_reason is not None
    assert "high_risk_constraints" in updated.critic_activation_reason


@pytest.mark.anyio
async def test_manual_off_policy_keeps_critic_disabled():
    store = DummyStore(_state("manual_off", details="请严格复核"))
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    payload = ReviewerSummaryV2(
        verdict="有条件通过",
        hard_gates=[ReviewerHardGateV2(name="目标-证据一致性", status="pass", note="")],
        key_issues=["问题1", "问题2", "问题3"],
        rubric_scores=[],
        suggested_rerun_agents=["Package"],
        lead_note="边界场景",
    )
    with patch("src.gateway.routers.education_runs.get_education_store", return_value=store):
        updated = await set_reviewer_summary("run_1", payload, actor)

    assert updated.critic_policy == "manual_off"
    assert updated.critic_enabled is False
    assert updated.critic_activation_reason == "manual_off"
