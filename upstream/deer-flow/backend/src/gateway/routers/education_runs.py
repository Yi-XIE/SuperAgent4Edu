"""Education run APIs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CriticSummaryV2,
    EducationRunState,
    MemorySignalUsage,
    ReviewerSummaryV2,
    UpdateRunRequest,
)
from src.education.signals import get_used_signals, record_used_signals
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/runs",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_runs_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _get_run(projectless_run_id: str, actor: ActorContext) -> EducationRunState:
    store = get_education_store()
    state = store.read_state()
    raw = state["runs"].get(projectless_run_id)
    if not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Run not found")
    run = EducationRunState(**raw)
    _guard_org(actor, run.org_id)
    return run


@router.get("/{run_id}", response_model=EducationRunState, summary="Get run")
async def get_run(run_id: str, actor: ActorContext = Depends(require_permission_dep("run:read"))) -> EducationRunState:
    return _get_run(run_id, actor)


@router.patch("/{run_id}", response_model=EducationRunState, summary="Update run")
async def update_run(
    run_id: str,
    payload: UpdateRunRequest,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["runs"].get(run_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**raw)
        _guard_org(actor, run.org_id)
        if payload.status is not None:
            run.status = payload.status
        if payload.current_stage is not None:
            run.current_stage = payload.current_stage
        if payload.rerun_targets is not None:
            run.rerun_targets = payload.rerun_targets
        if payload.artifact_paths is not None:
            run.artifact_paths = payload.artifact_paths
        run.updated_at = _now()
        state["runs"][run_id] = run.model_dump()
        return state["runs"][run_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="run.update", entity_type="run", entity_id=run_id)
    return EducationRunState(**updated)


@router.post("/{run_id}/reviewer-summary", response_model=EducationRunState, summary="Attach reviewer summary")
async def set_reviewer_summary(
    run_id: str,
    payload: ReviewerSummaryV2,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["runs"].get(run_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**raw)
        _guard_org(actor, run.org_id)
        run.reviewer_summary = payload
        run.updated_at = _now()
        state["runs"][run_id] = run.model_dump()
        return state["runs"][run_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="run.reviewer_summary.set", entity_type="run", entity_id=run_id)
    return EducationRunState(**updated)


@router.post("/{run_id}/critic-summary", response_model=EducationRunState, summary="Attach critic summary")
async def set_critic_summary(
    run_id: str,
    payload: CriticSummaryV2,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["runs"].get(run_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**raw)
        _guard_org(actor, run.org_id)
        run.critic_summary = payload
        run.updated_at = _now()
        state["runs"][run_id] = run.model_dump()
        return state["runs"][run_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="run.critic_summary.set", entity_type="run", entity_id=run_id)
    return EducationRunState(**updated)


@router.post("/{run_id}/publish-pptx", response_model=EducationRunState, summary="Mark optional PPTX generation step")
async def publish_pptx(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["runs"].get(run_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**raw)
        _guard_org(actor, run.org_id)
        if "/mnt/user-data/outputs/course-deck.pptx" not in run.artifact_paths:
            run.artifact_paths.append("/mnt/user-data/outputs/course-deck.pptx")
        run.updated_at = _now()
        state["runs"][run_id] = run.model_dump()
        return state["runs"][run_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="run.publish_pptx", entity_type="run", entity_id=run_id)
    return EducationRunState(**updated)


@router.get("/{run_id}/signals", response_model=list[MemorySignalUsage], summary="Get used memory signals for run")
async def get_run_signals(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> list[MemorySignalUsage]:
    run = _get_run(run_id, actor)
    _guard_org(actor, run.org_id)
    raw = get_used_signals(run_id)
    return [MemorySignalUsage(**item) for item in raw]


@router.post("/{run_id}/signals", response_model=list[MemorySignalUsage], summary="Upsert used memory signals")
async def upsert_run_signals(
    run_id: str,
    payload: list[MemorySignalUsage],
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> list[MemorySignalUsage]:
    run = _get_run(run_id, actor)
    _guard_org(actor, run.org_id)
    stored = record_used_signals(run_id, [item.model_dump() for item in payload], source="manual")
    return [MemorySignalUsage(**item) for item in stored]
