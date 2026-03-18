"""Teacher feedback APIs for education runs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import ActorContext, CreateTeachingFeedbackRequest, EducationRunState, TeachingAsset, TeachingFeedback
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/feedback",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_feedback_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


@router.get("", response_model=list[TeachingFeedback], summary="List teaching feedback")
async def list_feedback(
    run_id: str | None = None,
    actor: ActorContext = Depends(require_permission_dep("feedback:read")),
) -> list[TeachingFeedback]:
    store = get_education_store()
    state = store.read_state()
    items = [TeachingFeedback(**row) for row in state["feedback"].values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        items = [item for item in items if item.org_id == actor.org_id]
    if run_id:
        items = [item for item in items if item.run_id == run_id]
    return sorted(items, key=lambda item: item.created_at, reverse=True)


@router.post("", response_model=TeachingFeedback, summary="Create teaching feedback")
async def create_feedback(
    payload: CreateTeachingFeedbackRequest,
    actor: ActorContext = Depends(require_permission_dep("feedback:write")),
) -> TeachingFeedback:
    _guard_org(actor, payload.org_id)
    store = get_education_store()

    feedback = TeachingFeedback(
        id=store.generate_id("feedback"),
        org_id=payload.org_id,
        run_id=payload.run_id,
        user_id=actor.user_id,
        used_sections=payload.used_sections,
        changed_sections=payload.changed_sections,
        ineffective_sections=payload.ineffective_sections,
        asset_ids=payload.asset_ids,
        summary=payload.summary,
        rating=payload.rating,
        source=payload.source,
        submission_id=payload.submission_id,
    )

    def _mutate(state: dict):
        run_raw = state["runs"].get(payload.run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        _guard_org(actor, run.org_id)
        state["feedback"][feedback.id] = feedback.model_dump()

        for asset_id in payload.asset_ids:
            raw_asset = state["assets"].get(asset_id)
            if not isinstance(raw_asset, dict):
                continue
            asset = TeachingAsset(**raw_asset)
            if asset.org_id != run.org_id:
                continue
            asset.usage_count += 1
            asset.updated_at = _now()
            state["assets"][asset.id] = asset.model_dump()

        run.details = payload.summary or run.details
        run.updated_at = _now()
        state["runs"][run.id] = run.model_dump()
        return state["feedback"][feedback.id]

    created = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="feedback.create",
        entity_type="run",
        entity_id=payload.run_id,
        details={"feedback_id": feedback.id, "asset_ids": payload.asset_ids, "rating": payload.rating},
    )
    return TeachingFeedback(**created)
