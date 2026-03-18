"""Education teaching asset APIs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CreateTeachingAssetRequest,
    TeachingAsset,
    UpdateTeachingAssetRequest,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/assets",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_assets_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


@router.get("", response_model=list[TeachingAsset], summary="List teaching assets")
async def list_assets(
    run_id: str | None = None,
    asset_type: str | None = None,
    q: str | None = None,
    include_archived: bool = False,
    actor: ActorContext = Depends(require_permission_dep("asset:read")),
) -> list[TeachingAsset]:
    store = get_education_store()
    state = store.read_state()
    items = [TeachingAsset(**row) for row in state["assets"].values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        items = [item for item in items if item.org_id == actor.org_id]
    if run_id:
        items = [item for item in items if item.source_run_id == run_id]
    if asset_type:
        items = [item for item in items if item.asset_type == asset_type]
    if not include_archived:
        items = [item for item in items if item.status != "archived"]
    if q:
        needle = q.strip().lower()
        if needle:
            items = [
                item
                for item in items
                if needle in item.title.lower()
                or needle in item.content.lower()
                or any(needle in tag.lower() for tag in item.tags)
            ]
    return sorted(items, key=lambda item: item.updated_at, reverse=True)


@router.post("", response_model=TeachingAsset, summary="Create teaching asset")
async def create_asset(
    payload: CreateTeachingAssetRequest,
    actor: ActorContext = Depends(require_permission_dep("asset:write")),
) -> TeachingAsset:
    _guard_org(actor, payload.org_id)
    store = get_education_store()
    asset = TeachingAsset(
        id=store.generate_id("asset"),
        org_id=payload.org_id,
        asset_type=payload.asset_type,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        grade_band=payload.grade_band,
        domain_focus=payload.domain_focus,
        source_run_id=payload.source_run_id,
        source_path=payload.source_path,
        confidence=payload.confidence,
        visibility=payload.visibility,
        created_by=actor.user_id,
    )

    def _mutate(state: dict):
        state["assets"][asset.id] = asset.model_dump()
        return state["assets"][asset.id]

    created = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="asset.create",
        entity_type="asset",
        entity_id=asset.id,
        details={"source_run_id": payload.source_run_id, "asset_type": payload.asset_type},
    )
    return TeachingAsset(**created)


@router.patch("/{asset_id}", response_model=TeachingAsset, summary="Update teaching asset")
async def update_asset(
    asset_id: str,
    payload: UpdateTeachingAssetRequest,
    actor: ActorContext = Depends(require_permission_dep("asset:write")),
) -> TeachingAsset:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["assets"].get(asset_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Asset not found")
        asset = TeachingAsset(**raw)
        _guard_org(actor, asset.org_id)
        if payload.title is not None:
            asset.title = payload.title
        if payload.content is not None:
            asset.content = payload.content
        if payload.tags is not None:
            asset.tags = payload.tags
        if payload.grade_band is not None:
            asset.grade_band = payload.grade_band
        if payload.domain_focus is not None:
            asset.domain_focus = payload.domain_focus
        if payload.confidence is not None:
            asset.confidence = payload.confidence
        if payload.usage_count is not None:
            asset.usage_count = payload.usage_count
        if payload.visibility is not None:
            asset.visibility = payload.visibility
        if payload.status is not None:
            asset.status = payload.status
        asset.updated_at = _now()
        state["assets"][asset_id] = asset.model_dump()
        return state["assets"][asset_id]

    updated = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="asset.update",
        entity_type="asset",
        entity_id=asset_id,
    )
    return TeachingAsset(**updated)
