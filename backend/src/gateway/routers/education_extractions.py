"""Asset retrieval/extraction APIs for education runs."""

from datetime import datetime, timezone
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    AssetExtractionCandidate,
    EducationRunState,
    TeachingAsset,
    TeachingAssetType,
    UpsertExtractionRequest,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/extractions",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_extractions_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _infer_asset_type(path: str) -> TeachingAssetType:
    name = path.lower()
    if "kit" in name:
        return "learning_kit_plan"
    if "ubd" in name:
        return "goal_fragment"
    if "reference" in name:
        return "reference_note"
    if "ppt" in name:
        return "expression_template"
    return "activity_idea"


def _fallback_artifacts(run: EducationRunState) -> list[str]:
    if run.artifact_paths:
        return run.artifact_paths
    return [
        "/mnt/user-data/outputs/ubd-course-card.md",
        "/mnt/user-data/outputs/lesson-plan.md",
        "/mnt/user-data/outputs/ppt-outline.md",
        "/mnt/user-data/outputs/learning-kit-appendix.md",
        "/mnt/user-data/outputs/reference-summary.md",
    ]


def _build_default_candidates(state: dict, run: EducationRunState) -> list[AssetExtractionCandidate]:
    store = get_education_store()
    resources = [
        row
        for row in state.get("resources", {}).values()
        if isinstance(row, dict)
        and row.get("org_id") == run.org_id
        and bool(row.get("whitelisted", True))
    ]
    tags: list[str] = []
    for item in resources:
        for tag in item.get("tags", []):
            if isinstance(tag, str) and tag and tag not in tags:
                tags.append(tag)
            if len(tags) >= 6:
                break
        if len(tags) >= 6:
            break

    existing_assets = [
        TeachingAsset(**row)
        for row in state.get("assets", {}).values()
        if isinstance(row, dict)
        and row.get("org_id") == run.org_id
        and row.get("status", "active") == "active"
    ]
    existing_assets.sort(key=lambda item: (item.usage_count, item.updated_at), reverse=True)
    if not run.asset_retrieval_notes:
        run.asset_retrieval_notes = [f"{item.title}（复用 {item.usage_count} 次）" for item in existing_assets[:3]]
    if not run.selected_asset_ids:
        run.selected_asset_ids = [item.id for item in existing_assets[:3]]
    if run.retrieval_snapshot_at is None:
        run.retrieval_snapshot_at = _now()
    run.updated_at = _now()

    candidates: list[AssetExtractionCandidate] = []
    for artifact in _fallback_artifacts(run):
        filename = PurePosixPath(artifact).name
        stem = PurePosixPath(artifact).stem.replace("-", " ")
        candidates.append(
            AssetExtractionCandidate(
                id=store.generate_id("extract"),
                org_id=run.org_id,
                run_id=run.id,
                asset_type=_infer_asset_type(filename),
                title=f"{stem} 片段",
                content=f"从 {filename} 提取的可复用教学片段。",
                source_path=artifact,
                suggested_tags=tags[:4],
                suggested_visibility="private",
                status="candidate",
            )
        )
    if run.asset_extraction_status == "pending":
        run.asset_extraction_status = "ready_for_confirmation"
        run.current_stage = "Checkpoint 4 Asset Extraction"
    return candidates


@router.get("/{run_id}", response_model=list[AssetExtractionCandidate], summary="Get extraction candidates for run")
async def get_extraction_candidates(
    run_id: str,
    actor: ActorContext = Depends(require_permission_dep("extraction:read")),
) -> list[AssetExtractionCandidate]:
    store = get_education_store()

    def _mutate(state: dict):
        run_raw = state["runs"].get(run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        _guard_org(actor, run.org_id)

        raw_candidates = state["extractions"].get(run_id)
        if isinstance(raw_candidates, list) and raw_candidates:
            state["runs"][run_id] = run.model_dump()
            return raw_candidates

        generated = _build_default_candidates(state, run)
        generated_rows = [item.model_dump() for item in generated]
        state["extractions"][run_id] = generated_rows
        state["runs"][run_id] = run.model_dump()
        return generated_rows

    rows = store.transaction(_mutate)
    return [AssetExtractionCandidate(**row) for row in rows if isinstance(row, dict)]


@router.post("/{run_id}", response_model=list[AssetExtractionCandidate], summary="Upsert or confirm extraction candidates")
async def upsert_or_confirm_extractions(
    run_id: str,
    payload: UpsertExtractionRequest,
    actor: ActorContext = Depends(require_permission_dep("extraction:write")),
) -> list[AssetExtractionCandidate]:
    store = get_education_store()

    def _mutate(state: dict):
        run_raw = state["runs"].get(run_id)
        if not isinstance(run_raw, dict):
            raise HTTPException(status_code=404, detail="Run not found")
        run = EducationRunState(**run_raw)
        _guard_org(actor, run.org_id)

        existing = state["extractions"].get(run_id)
        if isinstance(existing, list):
            candidates = [AssetExtractionCandidate(**row) for row in existing if isinstance(row, dict)]
        else:
            candidates = _build_default_candidates(state, run)

        if payload.mode == "upsert":
            if payload.candidates:
                updated: list[AssetExtractionCandidate] = []
                for row in payload.candidates:
                    updated.append(
                        AssetExtractionCandidate(
                            id=row.id or store.generate_id("extract"),
                            org_id=run.org_id,
                            run_id=run.id,
                            asset_type=row.asset_type,
                            title=row.title,
                            content=row.content,
                            source_path=row.source_path,
                            suggested_tags=row.suggested_tags,
                            suggested_visibility=row.suggested_visibility,
                            status="candidate",
                        )
                    )
                candidates = updated
            run.asset_extraction_status = "ready_for_confirmation"
            run.current_stage = "Checkpoint 4 Asset Extraction"
        else:
            option = payload.option or "一键入库"
            if option == "跳过本轮":
                for item in candidates:
                    item.status = "skipped"
                    item.updated_at = _now()
                run.asset_extraction_status = "skipped"
                run.current_stage = "Asset Extraction Skipped"
            else:
                selected_ids = set(payload.selected_ids or [item.id for item in candidates])
                selected_asset_ids = set(run.selected_asset_ids)
                for item in candidates:
                    if item.id not in selected_ids:
                        item.status = "skipped"
                        item.updated_at = _now()
                        continue
                    item.status = "accepted"
                    item.updated_at = _now()
                    tags = payload.classifications.get(item.id, item.suggested_tags)
                    asset = TeachingAsset(
                        id=store.generate_id("asset"),
                        org_id=run.org_id,
                        asset_type=item.asset_type,
                        title=item.title,
                        content=item.content,
                        tags=tags,
                        grade_band="elementary",
                        domain_focus=[],
                        source_run_id=run.id,
                        source_path=item.source_path,
                        confidence=0.66,
                        usage_count=1,
                        visibility=item.suggested_visibility,
                        created_by=actor.user_id,
                    )
                    state["assets"][asset.id] = asset.model_dump()
                    selected_asset_ids.add(asset.id)
                run.selected_asset_ids = sorted(selected_asset_ids)
                run.asset_extraction_status = "confirmed"
                run.current_stage = "Asset Extraction Confirmed"
            run.status = "accepted"

        run.updated_at = _now()
        state["runs"][run_id] = run.model_dump()
        rows = [item.model_dump() for item in candidates]
        state["extractions"][run_id] = rows
        return rows

    rows = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="extraction.upsert_or_confirm",
        entity_type="run",
        entity_id=run_id,
        details={"mode": payload.mode, "option": payload.option, "selected": len(payload.selected_ids)},
    )
    return [AssetExtractionCandidate(**row) for row in rows if isinstance(row, dict)]
