"""Student platform APIs for assignments and submissions."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CreateStudentTaskRequest,
    ReviewSubmissionRequest,
    StudentSubmission,
    StudentTask,
    SubmitStudentTaskRequest,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/student",
    tags=["student"],
    dependencies=[Depends(make_rate_limiter("education_student_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


@router.get("/tasks", response_model=list[StudentTask], summary="List student tasks")
async def list_student_tasks(
    actor: ActorContext = Depends(require_permission_dep("student:read")),
) -> list[StudentTask]:
    store = get_education_store()
    state = store.read_state()
    tasks = [StudentTask(**row) for row in state["student_tasks"].values() if isinstance(row, dict)]
    if actor.role == "platform_admin":
        return tasks
    org_tasks = [task for task in tasks if task.org_id == actor.org_id]
    if actor.role == "student":
        return [task for task in org_tasks if actor.user_id in task.assigned_to]
    return org_tasks


@router.post("/tasks", response_model=StudentTask, summary="Create student task from course run")
async def create_student_task(
    payload: CreateStudentTaskRequest,
    actor: ActorContext = Depends(require_permission_dep("student:write")),
) -> StudentTask:
    _guard_org(actor, payload.org_id)
    store = get_education_store()
    task = StudentTask(
        id=store.generate_id("task"),
        org_id=payload.org_id,
        project_id=payload.project_id,
        run_id=payload.run_id,
        title=payload.title,
        description=payload.description,
        assigned_to=payload.assigned_to,
        due_at=payload.due_at,
        created_by=actor.user_id,
    )

    def _mutate(state: dict):
        if payload.run_id not in state["runs"]:
            raise HTTPException(status_code=404, detail="Run not found")
        state["student_tasks"][task.id] = task.model_dump()
        return state["student_tasks"][task.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="student.task.create", entity_type="student_task", entity_id=task.id)
    return StudentTask(**created)


@router.post("/tasks/{task_id}/submit", response_model=StudentSubmission, summary="Submit student task")
async def submit_student_task(
    task_id: str,
    payload: SubmitStudentTaskRequest,
    actor: ActorContext = Depends(require_permission_dep("student:write")),
) -> StudentSubmission:
    _guard_org(actor, payload.org_id)
    store = get_education_store()
    submission = StudentSubmission(
        id=store.generate_id("submission"),
        org_id=payload.org_id,
        task_id=task_id,
        student_user_id=actor.user_id,
        content=payload.content,
        attachments=payload.attachments,
    )

    def _mutate(state: dict):
        task_raw = state["student_tasks"].get(task_id)
        if not isinstance(task_raw, dict):
            raise HTTPException(status_code=404, detail="Task not found")
        task = StudentTask(**task_raw)
        if task.org_id != payload.org_id:
            raise HTTPException(status_code=400, detail="org_id mismatch with task")
        if actor.role == "student" and actor.user_id not in task.assigned_to:
            raise HTTPException(status_code=403, detail="Task not assigned to current student")
        state["student_submissions"][submission.id] = submission.model_dump()
        return state["student_submissions"][submission.id]

    created = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="student.task.submit",
        entity_type="student_submission",
        entity_id=submission.id,
        details={"task_id": task_id},
    )
    return StudentSubmission(**created)


@router.get("/submissions", response_model=list[StudentSubmission], summary="List submissions")
async def list_submissions(
    task_id: str | None = None,
    actor: ActorContext = Depends(require_permission_dep("student:read")),
) -> list[StudentSubmission]:
    store = get_education_store()
    state = store.read_state()
    rows = [StudentSubmission(**row) for row in state["student_submissions"].values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        rows = [row for row in rows if row.org_id == actor.org_id]
    if task_id:
        rows = [row for row in rows if row.task_id == task_id]
    if actor.role == "student":
        rows = [row for row in rows if row.student_user_id == actor.user_id]
    return rows


@router.patch("/submissions/{submission_id}/review", response_model=StudentSubmission, summary="Teacher review submission")
async def review_submission(
    submission_id: str,
    payload: ReviewSubmissionRequest,
    actor: ActorContext = Depends(require_permission_dep("student:write")),
) -> StudentSubmission:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["student_submissions"].get(submission_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Submission not found")
        submission = StudentSubmission(**raw)
        _guard_org(actor, submission.org_id)
        submission.score = payload.score
        submission.teacher_feedback = payload.teacher_feedback
        submission.reviewed_at = _now()
        state["student_submissions"][submission_id] = submission.model_dump()
        return state["student_submissions"][submission_id]

    updated = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="student.submission.review",
        entity_type="student_submission",
        entity_id=submission_id,
    )
    return StudentSubmission(**updated)
