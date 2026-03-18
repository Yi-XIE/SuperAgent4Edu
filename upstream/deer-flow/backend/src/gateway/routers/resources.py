"""Resource library APIs for education domain."""

import ipaddress
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CreateResourceRequest,
    EducationResource,
    UpdateResourceRequest,
)
from src.education.store import get_education_store

_ALLOWED_RESOURCE_DOMAINS = {
    domain.strip().lower()
    for domain in os.getenv("EDUCATION_RESOURCE_ALLOWED_DOMAINS", "").split(",")
    if domain.strip()
}

router = APIRouter(
    prefix="/api/resources",
    tags=["resources"],
    dependencies=[Depends(make_rate_limiter("education_resources_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


def _validate_resource_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Resource URL must use http/https")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Resource URL host is required")

    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".local"):
        raise HTTPException(status_code=400, detail="Localhost/local domains are not allowed")

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=400, detail="Private network addresses are not allowed")
    except ValueError:
        # Not an IP literal, continue domain checks
        pass

    if _ALLOWED_RESOURCE_DOMAINS and not any(
        host == domain or host.endswith(f".{domain}") for domain in _ALLOWED_RESOURCE_DOMAINS
    ):
        raise HTTPException(status_code=400, detail="Resource domain is not in allowlist")


@router.get("", response_model=list[EducationResource], summary="List resources")
async def list_resources(
    q: str | None = None,
    tag: str | None = None,
    whitelisted_only: bool = True,
    actor: ActorContext = Depends(require_permission_dep("resource:read")),
) -> list[EducationResource]:
    store = get_education_store()
    state = store.read_state()
    rows = [EducationResource(**row) for row in state["resources"].values() if isinstance(row, dict)]
    if actor.role != "platform_admin":
        rows = [row for row in rows if row.org_id == actor.org_id]
    if whitelisted_only:
        rows = [row for row in rows if row.whitelisted]
    if tag:
        rows = [row for row in rows if tag in row.tags]
    if q:
        keyword = q.lower().strip()
        rows = [row for row in rows if keyword in row.title.lower() or keyword in row.summary.lower()]
    return rows


@router.post("", response_model=EducationResource, summary="Create resource")
async def create_resource(
    payload: CreateResourceRequest,
    actor: ActorContext = Depends(require_permission_dep("resource:write")),
) -> EducationResource:
    _guard_org(actor, payload.org_id)
    _validate_resource_url(payload.url)
    store = get_education_store()
    item = EducationResource(
        id=store.generate_id("res"),
        org_id=payload.org_id,
        title=payload.title,
        url=payload.url,
        source_type=payload.source_type,
        tags=payload.tags,
        whitelisted=payload.whitelisted,
        summary=payload.summary,
        created_by=actor.user_id,
    )

    def _mutate(state: dict):
        state["resources"][item.id] = item.model_dump()
        return state["resources"][item.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="resource.create", entity_type="resource", entity_id=item.id)
    return EducationResource(**created)


@router.patch("/{resource_id}", response_model=EducationResource, summary="Update resource")
async def update_resource(
    resource_id: str,
    payload: UpdateResourceRequest,
    actor: ActorContext = Depends(require_permission_dep("resource:write")),
) -> EducationResource:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["resources"].get(resource_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Resource not found")
        item = EducationResource(**raw)
        _guard_org(actor, item.org_id)
        if payload.title is not None:
            item.title = payload.title
        if payload.url is not None:
            _validate_resource_url(payload.url)
            item.url = payload.url
        if payload.source_type is not None:
            item.source_type = payload.source_type
        if payload.tags is not None:
            item.tags = payload.tags
        if payload.whitelisted is not None:
            item.whitelisted = payload.whitelisted
        if payload.summary is not None:
            item.summary = payload.summary
        item.updated_at = _now()
        state["resources"][resource_id] = item.model_dump()
        return state["resources"][resource_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="resource.update", entity_type="resource", entity_id=resource_id)
    return EducationResource(**updated)


@router.delete("/{resource_id}", summary="Delete resource")
async def delete_resource(
    resource_id: str,
    actor: ActorContext = Depends(require_permission_dep("resource:write")),
) -> dict:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["resources"].get(resource_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Resource not found")
        item = EducationResource(**raw)
        _guard_org(actor, item.org_id)
        del state["resources"][resource_id]
        return {"ok": True}

    result = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="resource.delete", entity_type="resource", entity_id=resource_id)
    return result
