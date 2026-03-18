"""Student submit-review-feedback closed-loop contracts."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from src.education.schemas import (
    ActorContext,
    EducationRunState,
    ReviewSubmissionRequest,
    SubmitStudentTaskRequest,
)
from src.gateway.routers.student import review_submission, submit_student_task


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
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="学生端闭环测试",
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
        "student_tasks": {
            "task_1": {
                "id": "task_1",
                "org_id": "org_1",
                "project_id": "proj_1",
                "run_id": "run_1",
                "title": "课堂任务",
                "description": "提交作品",
                "assigned_to": ["student_1"],
                "due_at": None,
                "created_by": "teacher_1",
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            }
        },
        "student_submissions": {},
        "run_signals": {},
        "audit_logs": [],
    }


@pytest.mark.anyio
async def test_student_submit_then_teacher_review_generates_feedback():
    store = DummyStore(_state())
    student_actor = ActorContext(user_id="student_1", org_id="org_1", role="student")
    teacher_actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")

    with patch("src.gateway.routers.student.get_education_store", return_value=store):
        submission = await submit_student_task(
            "task_1",
            SubmitStudentTaskRequest(
                org_id="org_1",
                task_id="task_1",
                content="这是我的提交作品与思考。",
            ),
            student_actor,
        )
        reviewed = await review_submission(
            submission.id,
            ReviewSubmissionRequest(score=4.5, teacher_feedback="证据链清晰，可优化展示节奏。"),
            teacher_actor,
        )

    assert reviewed.score == 4.5
    assert reviewed.teacher_feedback == "证据链清晰，可优化展示节奏。"
    assert len(store.state["feedback"]) == 1
    feedback = next(iter(store.state["feedback"].values()))
    assert feedback["source"] == "student_review"
    assert feedback["submission_id"] == submission.id
    assert feedback["run_id"] == "run_1"
