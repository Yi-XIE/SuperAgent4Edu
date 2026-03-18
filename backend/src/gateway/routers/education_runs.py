"""Education run APIs."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from src.config.paths import get_paths
from src.education.audit import write_audit_log
from src.education.bootstrap import bootstrap_run_state
from src.education.critic_policy import evaluate_critic_activation
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CriticSummaryV2,
    CourseBlueprint,
    CoursePackage,
    EducationRunState,
    EducationRunResult,
    MemorySignalUsage,
    ReviewerSummaryV2,
    UpdateRunRequest,
)
from src.education.signals import get_used_signals, record_used_signals
from src.education.store import get_education_store
from src.education.workflow_template import get_workflow_template_content, guard_max_local_rework

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


def _find_blueprint_row(state: dict, *, run_id: str, org_id: str) -> tuple[str | None, dict | None]:
    for blueprint_id, raw in state.get("course_blueprints", {}).items():
        if not isinstance(raw, dict):
            continue
        if raw.get("run_id") != run_id or raw.get("org_id") != org_id:
            continue
        return blueprint_id, raw
    return None, None


def _find_package_row(state: dict, *, run_id: str, org_id: str) -> tuple[str | None, dict | None]:
    for package_id, raw in state.get("course_packages", {}).items():
        if not isinstance(raw, dict):
            continue
        if raw.get("run_id") != run_id or raw.get("org_id") != org_id:
            continue
        return package_id, raw
    return None, None


def _artifact_exists(thread_id: str | None, artifact_path: str) -> bool:
    if not thread_id or not artifact_path.startswith("/mnt/user-data/"):
        return False
    try:
        resolved = get_paths().resolve_virtual_path(thread_id, artifact_path)
    except Exception:
        return False
    return isinstance(resolved, Path) and resolved.exists()


@router.get("/{run_id}", response_model=EducationRunState, summary="Get run")
async def get_run(run_id: str, actor: ActorContext = Depends(require_permission_dep("run:read"))) -> EducationRunState:
    return _get_run(run_id, actor)


@router.post("/{run_id}/bootstrap", response_model=EducationRunState, summary="Bootstrap run before first CP1")
async def bootstrap_run(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        run_raw = state["runs"].get(run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        _guard_org(actor, run.org_id)
        bootstrap_run_state(state, run)
        state["runs"][run.id] = run.model_dump()
        return state["runs"][run.id]

    updated = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="run.bootstrap",
        entity_type="run",
        entity_id=run_id,
    )
    return EducationRunState(**updated)


@router.get("/{run_id}/result", response_model=EducationRunResult, summary="Get aggregated run result")
async def get_run_result(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> EducationRunResult:
    store = get_education_store()
    state = store.read_state()

    run_raw = state["runs"].get(run_id)
    if not isinstance(run_raw, dict):
        raise HTTPException(status_code=404, detail="Run not found")
    run = EducationRunState(**run_raw)
    _guard_org(actor, run.org_id)

    _, blueprint_row = _find_blueprint_row(state, run_id=run.id, org_id=run.org_id)
    _, package_row = _find_package_row(state, run_id=run.id, org_id=run.org_id)

    parse_errors: list[str] = []
    blueprint: CourseBlueprint | None = None
    package: CoursePackage | None = None
    if blueprint_row is None:
        parse_errors.append("blueprint_not_found")
    else:
        blueprint = CourseBlueprint(**blueprint_row)
    if package_row is None:
        parse_errors.append("package_not_found")
    else:
        package = CoursePackage(**package_row)

    extraction_rows = state.get("extractions", {}).get(run.id)
    extraction_candidates = []
    if isinstance(extraction_rows, list):
        extraction_candidates = [row for row in extraction_rows if isinstance(row, dict)]

    extracted_assets = []
    selected_ids = set(run.selected_asset_ids)
    for raw_asset in state.get("assets", {}).values():
        if not isinstance(raw_asset, dict):
            continue
        if raw_asset.get("org_id") != run.org_id:
            continue
        if raw_asset.get("source_run_id") == run.id or raw_asset.get("id") in selected_ids:
            extracted_assets.append(raw_asset)

    candidate_paths: list[str] = []
    if run.artifact_paths:
        candidate_paths.extend(run.artifact_paths)
    elif package is not None:
        candidate_paths.extend(
            [
                package.lesson_plan_path,
                package.ppt_outline_path,
                package.learning_kit_path,
                package.reference_summary_path,
                package.artifact_manifest_path,
            ],
        )

    artifact_paths: list[str] = []
    for path in candidate_paths:
        if _artifact_exists(run.thread_id, path):
            artifact_paths.append(path)
        else:
            parse_errors.append(f"artifact_missing:{path}")

    result = EducationRunResult(
        run=run,
        blueprint=blueprint,
        package=package,
        artifact_paths=artifact_paths,
        parse_errors=parse_errors,
        extraction_candidates=extraction_candidates,
        extracted_assets=extracted_assets,
        retrieval_basis=run.asset_retrieval_notes,
    )
    return result


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
        if payload.thread_id is not None:
            run.thread_id = payload.thread_id
        if payload.bootstrap_status is not None:
            run.bootstrap_status = payload.bootstrap_status
        if payload.bootstrap_at is not None:
            run.bootstrap_at = payload.bootstrap_at
        if payload.generation_mode is not None:
            run.generation_mode = payload.generation_mode
        if payload.critic_enabled is not None:
            run.critic_enabled = payload.critic_enabled
            if payload.critic_policy is None:
                run.critic_policy = "manual_on" if payload.critic_enabled else "manual_off"
                run.critic_activation_reason = run.critic_policy
        if payload.critic_policy is not None:
            run.critic_policy = payload.critic_policy
        if payload.critic_activation_reason is not None:
            run.critic_activation_reason = payload.critic_activation_reason
        if payload.blueprint_status is not None:
            run.blueprint_status = payload.blueprint_status
        if payload.package_status is not None:
            run.package_status = payload.package_status
        if payload.asset_extraction_status is not None:
            run.asset_extraction_status = payload.asset_extraction_status
        if payload.workflow_template_id is not None:
            run.workflow_template_id = payload.workflow_template_id
        if payload.asset_retrieval_notes is not None:
            run.asset_retrieval_notes = payload.asset_retrieval_notes
        if payload.selected_asset_ids is not None:
            run.selected_asset_ids = payload.selected_asset_ids
        if payload.retrieval_snapshot_at is not None:
            run.retrieval_snapshot_at = payload.retrieval_snapshot_at
        if payload.rerun_targets is not None:
            run.rerun_targets = payload.rerun_targets
        if payload.artifact_paths is not None:
            run.artifact_paths = payload.artifact_paths

        if run.critic_policy == "manual_on":
            run.critic_enabled = True
            run.critic_activation_reason = run.critic_activation_reason or "manual_on"
        elif run.critic_policy == "manual_off":
            run.critic_enabled = False
            run.critic_activation_reason = run.critic_activation_reason or "manual_off"
        elif run.critic_policy == "auto":
            run.critic_enabled, run.critic_activation_reason = evaluate_critic_activation(
                run,
                run.reviewer_summary,
            )

        template_content = get_workflow_template_content(state, run)
        run.guard.max_local_rework = guard_max_local_rework(
            template_content,
            max(0, run.guard.max_local_rework),
        )

        if run.bootstrap_status != "ready" and (
            run.current_stage.startswith("Stage 0")
            or run.current_stage == "Checkpoint Pending"
            or "Checkpoint 1" in run.current_stage
        ):
            bootstrap_run_state(state, run)

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
        if run.critic_policy == "auto":
            run.critic_enabled, run.critic_activation_reason = evaluate_critic_activation(
                run,
                payload,
            )
        elif run.critic_policy == "manual_on":
            run.critic_enabled = True
            run.critic_activation_reason = "manual_on"
        elif run.critic_policy == "manual_off":
            run.critic_enabled = False
            run.critic_activation_reason = "manual_off"
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
