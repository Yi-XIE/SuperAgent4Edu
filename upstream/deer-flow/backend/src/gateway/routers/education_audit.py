"""Audit APIs for education platform governance."""

from fastapi import APIRouter, Depends

from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import ActorContext, AuditLogEntry
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/audit",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_audit_api", 240))],
)


@router.get("", response_model=list[AuditLogEntry], summary="List education audit logs")
async def list_audit_logs(
    limit: int = 200,
    actor: ActorContext = Depends(require_permission_dep("audit:read")),
) -> list[AuditLogEntry]:
    store = get_education_store()
    state = store.read_state()
    rows = [AuditLogEntry(**row) for row in state["audit_logs"] if isinstance(row, dict)]
    if actor.role == "platform_admin":
        return rows[-max(1, min(limit, 1000)) :]
    org_rows = [row for row in rows if row.org_id == actor.org_id]
    return org_rows[-max(1, min(limit, 1000)) :]
