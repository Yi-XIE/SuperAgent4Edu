"""Checkpoint decision APIs backed by deterministic education workflow state machine."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.bootstrap import bootstrap_run_state
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import ActorContext, CheckpointDecision, CheckpointDecisionResult, EducationRunState
from src.education.store import get_education_store
from src.education.workflow import apply_checkpoint_decision
from src.education.workflow_template import get_workflow_template_content

router = APIRouter(
    prefix="/api/education/checkpoints",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_checkpoints_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _resolve_run_row(state: dict, run_or_thread_id: str) -> tuple[str | None, dict | None]:
    raw = state.get("runs", {}).get(run_or_thread_id)
    if isinstance(raw, dict):
        return run_or_thread_id, raw
    for run_id, candidate in state.get("runs", {}).items():
        if not isinstance(candidate, dict):
            continue
        if candidate.get("thread_id") == run_or_thread_id:
            return run_id, candidate
    return None, None


@router.get("/{run_id}", response_model=EducationRunState, summary="Get checkpoint state for run")
async def get_checkpoint_state(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> EducationRunState:
    store = get_education_store()

    def _mutate(state: dict):
        resolved_run_id, raw = _resolve_run_row(state, run_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**raw)
        _guard_org(actor, run.org_id)
        if run.bootstrap_status != "ready" and (
            run.current_stage.startswith("Stage 0")
            or run.current_stage == "Checkpoint Pending"
            or "Checkpoint 1" in run.current_stage
        ):
            bootstrap_run_state(state, run)
            state["runs"][resolved_run_id or run.id] = run.model_dump()
            return state["runs"][resolved_run_id or run.id]
        return raw

    row = store.transaction(_mutate)
    return EducationRunState(**row)


@router.post("/{run_id}/decide", response_model=CheckpointDecisionResult, summary="Apply checkpoint decision")
async def decide_checkpoint(
    run_id: str,
    payload: CheckpointDecision,
    actor: ActorContext = Depends(require_permission_dep("checkpoint:write")),
) -> CheckpointDecisionResult:
    store = get_education_store()

    def _mutate(state: dict):
        resolved_run_id, raw = _resolve_run_row(state, run_id)
        if isinstance(raw, dict):
            run = EducationRunState(**raw)
            _guard_org(actor, run.org_id)
        else:
            # Auto-bootstrap run state for chat-first education flow where
            # thread_id is used as run_id before explicit project creation.
            run = EducationRunState(
                id=run_id,
                org_id=actor.org_id,
                project_id="proj_chat_bootstrap",
                title=f"Chat Run {run_id}",
                thread_id=run_id,
                status="awaiting_checkpoint",
                current_stage="Checkpoint Pending",
            )
            bootstrap_run_state(state, run)

        if payload.checkpoint_id == "cp1-task-confirmation" or run.bootstrap_status != "ready":
            bootstrap_run_state(state, run)

        template_content = get_workflow_template_content(state, run)
        if not payload.actor_user_id:
            payload.actor_user_id = actor.user_id
        result = apply_checkpoint_decision(
            run,
            payload,
            template_content=template_content,
        )
        result.run.updated_at = _now()
        state["runs"][resolved_run_id or result.run.id] = result.run.model_dump()
        return result

    result = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="checkpoint.decide",
        entity_type="run",
        entity_id=run_id,
        details={
            "checkpoint_id": payload.checkpoint_id,
            "option": payload.option,
            "normalized_option": result.normalized_option,
            "rerun_targets": result.rerun_targets,
            "reopened_to_cp1": result.reopened_to_cp1,
        },
    )
    return result
