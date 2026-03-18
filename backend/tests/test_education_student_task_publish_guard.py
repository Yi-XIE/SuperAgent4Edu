"""Contracts for publishing student tasks only from accepted runs."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.education.schemas import ActorContext, CreateStudentTaskRequest, EducationRunState
from src.gateway.routers.student import create_student_task


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


def _state(run_status: str) -> dict:
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="学生任务发布守卫",
        status=run_status,  # type: ignore[arg-type]
    )
    return {
        "orgs": {},
        "projects": {"proj_1": {"id": "proj_1", "org_id": "org_1", "name": "p", "owner_id": "teacher_1"}},
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
async def test_create_student_task_requires_run_accepted():
    store = DummyStore(_state("running"))
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    payload = CreateStudentTaskRequest(
        org_id="org_1",
        project_id="proj_1",
        run_id="run_1",
        title="任务",
        description="desc",
    )

    with patch("src.gateway.routers.student.get_education_store", return_value=store):
        with pytest.raises(HTTPException) as exc:
            await create_student_task(payload, actor)
    assert exc.value.status_code == 400
    assert "accepted" in str(exc.value.detail)


@pytest.mark.anyio
async def test_create_student_task_succeeds_when_run_accepted():
    store = DummyStore(_state("accepted"))
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    payload = CreateStudentTaskRequest(
        org_id="org_1",
        project_id="proj_1",
        run_id="run_1",
        title="任务",
        description="desc",
    )

    with patch("src.gateway.routers.student.get_education_store", return_value=store):
        created = await create_student_task(payload, actor)
    assert created.run_id == "run_1"
