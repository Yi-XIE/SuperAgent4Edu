"""Template marketplace APIs for education domain."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CreateTemplateRequest,
    EducationTemplate,
    UpdateTemplateRequest,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/templates",
    tags=["templates"],
    dependencies=[Depends(make_rate_limiter("education_templates_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


@router.get("", response_model=list[EducationTemplate], summary="List templates")
async def list_templates(
    template_type: str | None = None,
    actor: ActorContext = Depends(require_permission_dep("template:read")),
) -> list[EducationTemplate]:
    store = get_education_store()
    state = store.read_state()
    rows = [EducationTemplate(**row) for row in state["templates"].values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        rows = [row for row in rows if row.org_id == actor.org_id]
    if template_type:
        rows = [row for row in rows if row.type == template_type]
    return rows


@router.post("", response_model=EducationTemplate, summary="Create template")
async def create_template(
    payload: CreateTemplateRequest,
    actor: ActorContext = Depends(require_permission_dep("template:write")),
) -> EducationTemplate:
    _guard_org(actor, payload.org_id)
    store = get_education_store()
    item = EducationTemplate(
        id=store.generate_id("tpl"),
        org_id=payload.org_id,
        type=payload.type,
        name=payload.name,
        description=payload.description,
        content=payload.content,
        created_by=actor.user_id,
    )

    def _mutate(state: dict):
        state["templates"][item.id] = item.model_dump()
        return state["templates"][item.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="template.create", entity_type="template", entity_id=item.id)
    return EducationTemplate(**created)


@router.patch("/{template_id}", response_model=EducationTemplate, summary="Update template")
async def update_template(
    template_id: str,
    payload: UpdateTemplateRequest,
    actor: ActorContext = Depends(require_permission_dep("template:write")),
) -> EducationTemplate:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["templates"].get(template_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Template not found")
        item = EducationTemplate(**raw)
        _guard_org(actor, item.org_id)
        if payload.name is not None:
            item.name = payload.name
        if payload.description is not None:
            item.description = payload.description
        if payload.content is not None:
            item.content = payload.content
        if payload.status is not None:
            item.status = payload.status
        item.version += 1
        item.updated_at = _now()
        state["templates"][template_id] = item.model_dump()
        return state["templates"][template_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="template.update", entity_type="template", entity_id=template_id)
    return EducationTemplate(**updated)


@router.post("/{template_id}/publish", response_model=EducationTemplate, summary="Publish template")
async def publish_template(
    template_id: str,
    actor: ActorContext = Depends(require_permission_dep("template:write")),
) -> EducationTemplate:
    return await update_template(template_id, UpdateTemplateRequest(status="published"), actor)


@router.post("/{template_id}/import", response_model=EducationTemplate, summary="Import template into current org")
async def import_template(
    template_id: str,
    actor: ActorContext = Depends(require_permission_dep("template:write")),
) -> EducationTemplate:
    store = get_education_store()
    state = store.read_state()
    raw = state["templates"].get(template_id)
    if not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Template not found")
    source = EducationTemplate(**raw)
    copied = CreateTemplateRequest(
        org_id=actor.org_id,
        type=source.type,
        name=f"{source.name} (Imported)",
        description=source.description,
        content=source.content,
    )
    return await create_template(copied, actor)
