"""Course blueprint APIs for education runs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CourseBlueprint,
    CreateCourseBlueprintRequest,
    EducationRunState,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/blueprints",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_blueprints_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _find_blueprint_id(state: dict, *, run_id: str, org_id: str) -> str | None:
    for blueprint_id, raw in state.get("course_blueprints", {}).items():
        if not isinstance(raw, dict):
            continue
        if raw.get("run_id") != run_id:
            continue
        if raw.get("org_id") != org_id:
            continue
        return blueprint_id
    return None


@router.get("", response_model=list[CourseBlueprint], summary="List course blueprints")
async def list_blueprints(
    run_id: str | None = None,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> list[CourseBlueprint]:
    store = get_education_store()
    state = store.read_state()
    rows = [CourseBlueprint(**row) for row in state.get("course_blueprints", {}).values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        rows = [row for row in rows if row.org_id == actor.org_id]
    if run_id:
        rows = [row for row in rows if row.run_id == run_id]
    return sorted(rows, key=lambda row: row.updated_at, reverse=True)


@router.post("", response_model=CourseBlueprint, summary="Create or upsert a course blueprint")
async def upsert_blueprint(
    payload: CreateCourseBlueprintRequest,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> CourseBlueprint:
    _guard_org(actor, payload.org_id)
    store = get_education_store()

    def _mutate(state: dict):
        run_raw = state.get("runs", {}).get(payload.run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        if run.org_id != payload.org_id:
            raise HTTPException(status_code=400, detail="org_id mismatch with run")

        existing_id = _find_blueprint_id(state, run_id=payload.run_id, org_id=payload.org_id)
        if existing_id is not None:
            blueprint = CourseBlueprint(**state["course_blueprints"][existing_id])
            blueprint.title = payload.title
            blueprint.big_ideas = payload.big_ideas
            blueprint.essential_questions = payload.essential_questions
            blueprint.transfer_goals = payload.transfer_goals
            blueprint.project_direction = payload.project_direction
            blueprint.research_summary = payload.research_summary
            blueprint.source_brief_path = payload.source_brief_path
            blueprint.updated_at = _now()
            state["course_blueprints"][existing_id] = blueprint.model_dump()
            return state["course_blueprints"][existing_id]

        blueprint = CourseBlueprint(
            id=store.generate_id("blueprint"),
            org_id=payload.org_id,
            run_id=payload.run_id,
            title=payload.title,
            big_ideas=payload.big_ideas,
            essential_questions=payload.essential_questions,
            transfer_goals=payload.transfer_goals,
            project_direction=payload.project_direction,
            research_summary=payload.research_summary,
            source_brief_path=payload.source_brief_path,
        )
        state["course_blueprints"][blueprint.id] = blueprint.model_dump()
        return state["course_blueprints"][blueprint.id]

    row = store.transaction(_mutate)
    result = CourseBlueprint(**row)
    write_audit_log(
        store,
        actor=actor,
        action="blueprint.upsert",
        entity_type="course_blueprint",
        entity_id=result.id,
        details={"run_id": result.run_id},
    )
    return result
