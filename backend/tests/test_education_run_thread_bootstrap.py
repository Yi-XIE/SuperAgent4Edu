"""Contracts for run/thread binding, bootstrap endpoint, and strict result aggregation."""

from copy import deepcopy
from unittest.mock import patch
import uuid

import pytest

from src.education.schemas import ActorContext, CreateRunRequest, EducationRunState
from src.gateway.routers.education_checkpoints import decide_checkpoint
from src.gateway.routers.education_projects import create_project_run
from src.gateway.routers.education_runs import bootstrap_run, get_run_result


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


def _state() -> dict:
    return {
        "orgs": {},
        "projects": {
            "proj_1": {
                "id": "proj_1",
                "org_id": "org_1",
                "name": "课程项目",
                "description": "",
                "owner_id": "teacher_1",
                "status": "draft",
                "version": 1,
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            },
        },
        "runs": {},
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
async def test_create_run_with_start_chat_sets_thread_binding_and_bootstrap_fields():
    store = DummyStore(_state())
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    payload = CreateRunRequest(
        org_id="org_1",
        project_id="proj_1",
        title="绑定测试",
        start_chat=True,
    )
    with patch("src.gateway.routers.education_projects.get_education_store", return_value=store):
        created = await create_project_run("proj_1", payload, actor)

    assert created.thread_id is not None
    uuid.UUID(created.thread_id)
    assert created.bootstrap_status == "ready"
    assert created.bootstrap_at is not None
    assert created.retrieval_snapshot_at is not None


@pytest.mark.anyio
async def test_bootstrap_endpoint_is_idempotent_for_existing_run():
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="显式 bootstrap",
        thread_id=str(uuid.uuid4()),
        bootstrap_status="pending",
    )
    state = _state()
    state["runs"]["run_1"] = run.model_dump()
    store = DummyStore(state)
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")

    with patch("src.gateway.routers.education_runs.get_education_store", return_value=store):
        updated = await bootstrap_run("run_1", actor)

    assert updated.bootstrap_status == "ready"
    assert updated.bootstrap_at is not None
    assert updated.retrieval_snapshot_at is not None


@pytest.mark.anyio
async def test_run_result_no_placeholder_autofill_when_objects_missing():
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="严格聚合",
        thread_id=str(uuid.uuid4()),
        artifact_paths=["/mnt/user-data/outputs/lesson-plan.md"],
    )
    state = _state()
    state["runs"]["run_1"] = run.model_dump()
    store = DummyStore(state)
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")

    with patch("src.gateway.routers.education_runs.get_education_store", return_value=store):
        result = await get_run_result("run_1", actor)

    assert result.blueprint is None
    assert result.package is None
    assert "blueprint_not_found" in result.parse_errors
    assert "package_not_found" in result.parse_errors


@pytest.mark.anyio
async def test_checkpoint_decision_can_resolve_run_by_thread_id():
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="thread 兼容",
        thread_id="thread-abc",
        status="awaiting_checkpoint",
        current_stage="Checkpoint 1",
    )
    state = _state()
    state["runs"]["run_1"] = run.model_dump()
    store = DummyStore(state)
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")

    from src.education.schemas import CheckpointDecision

    with patch("src.gateway.routers.education_checkpoints.get_education_store", return_value=store):
        result = await decide_checkpoint(
            "thread-abc",
            CheckpointDecision(
                checkpoint_id="cp1-task-confirmation",
                option="继续并锁定当前任务约束",
            ),
            actor,
        )

    assert result.run.id == "run_1"
