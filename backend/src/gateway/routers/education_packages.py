"""Course package APIs for education runs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CoursePackage,
    CreateCoursePackageRequest,
    EducationRunState,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/packages",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_packages_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _find_package_id(state: dict, *, run_id: str, org_id: str) -> str | None:
    for package_id, raw in state.get("course_packages", {}).items():
        if not isinstance(raw, dict):
            continue
        if raw.get("run_id") != run_id:
            continue
        if raw.get("org_id") != org_id:
            continue
        return package_id
    return None


@router.get("", response_model=list[CoursePackage], summary="List course packages")
async def list_packages(
    run_id: str | None = None,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> list[CoursePackage]:
    store = get_education_store()
    state = store.read_state()
    rows = [CoursePackage(**row) for row in state.get("course_packages", {}).values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        rows = [row for row in rows if row.org_id == actor.org_id]
    if run_id:
        rows = [row for row in rows if row.run_id == run_id]
    return sorted(rows, key=lambda row: row.updated_at, reverse=True)


@router.post("", response_model=CoursePackage, summary="Create or upsert a course package")
async def upsert_package(
    payload: CreateCoursePackageRequest,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> CoursePackage:
    _guard_org(actor, payload.org_id)
    store = get_education_store()

    def _mutate(state: dict):
        run_raw = state.get("runs", {}).get(payload.run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        if run.org_id != payload.org_id:
            raise HTTPException(status_code=400, detail="org_id mismatch with run")

        existing_id = _find_package_id(state, run_id=payload.run_id, org_id=payload.org_id)
        if existing_id is not None:
            package = CoursePackage(**state["course_packages"][existing_id])
            package.blueprint_id = payload.blueprint_id
            package.summary = payload.summary
            package.lesson_plan_path = payload.lesson_plan_path
            package.ppt_outline_path = payload.ppt_outline_path
            package.learning_kit_path = payload.learning_kit_path
            package.reference_summary_path = payload.reference_summary_path
            package.artifact_manifest_path = payload.artifact_manifest_path
            package.updated_at = _now()
            state["course_packages"][existing_id] = package.model_dump()
            return state["course_packages"][existing_id]

        package = CoursePackage(
            id=store.generate_id("package"),
            org_id=payload.org_id,
            run_id=payload.run_id,
            blueprint_id=payload.blueprint_id,
            summary=payload.summary,
            lesson_plan_path=payload.lesson_plan_path,
            ppt_outline_path=payload.ppt_outline_path,
            learning_kit_path=payload.learning_kit_path,
            reference_summary_path=payload.reference_summary_path,
            artifact_manifest_path=payload.artifact_manifest_path,
        )
        state["course_packages"][package.id] = package.model_dump()
        return state["course_packages"][package.id]

    row = store.transaction(_mutate)
    result = CoursePackage(**row)
    write_audit_log(
        store,
        actor=actor,
        action="package.upsert",
        entity_type="course_package",
        entity_id=result.id,
        details={"run_id": result.run_id},
    )
    return result
