"""RBAC helpers for education platform APIs."""

from fastapi import Depends, Header, HTTPException, Request

from .schemas import ActorContext, OrgRole, PermissionMatrix

ROLE_PERMISSIONS: dict[OrgRole, set[str]] = {
    "platform_admin": {"*"},
    "org_admin": {
        "org:read",
        "org:write",
        "member:write",
        "project:read",
        "project:write",
        "run:read",
        "run:write",
        "checkpoint:write",
        "template:read",
        "template:write",
        "resource:read",
        "resource:write",
        "student:read",
        "student:write",
        "audit:read",
    },
    "curriculum_lead": {
        "org:read",
        "project:read",
        "project:write",
        "run:read",
        "run:write",
        "checkpoint:write",
        "template:read",
        "template:write",
        "resource:read",
        "resource:write",
        "student:read",
        "student:write",
    },
    "teacher": {
        "org:read",
        "project:read",
        "project:write",
        "run:read",
        "run:write",
        "checkpoint:write",
        "template:read",
        "resource:read",
        "resource:write",
        "student:read",
        "student:write",
    },
    "reviewer": {
        "org:read",
        "project:read",
        "run:read",
        "run:write",
        "checkpoint:write",
        "template:read",
        "resource:read",
        "student:read",
    },
    "student": {
        "org:read",
        "project:read",
        "run:read",
        "resource:read",
        "student:read",
        "student:write",
    },
}


async def get_actor_context(
    request: Request,
    x_edu_user_id: str | None = Header(default=None),
    x_edu_org_id: str | None = Header(default=None),
    x_edu_role: str | None = Header(default=None),
) -> ActorContext:
    """Build actor context from headers with safe local defaults."""
    role: OrgRole
    if x_edu_role in ROLE_PERMISSIONS:
        role = x_edu_role  # type: ignore[assignment]
    else:
        role = "org_admin"
    actor = ActorContext(
        user_id=x_edu_user_id or "dev-user",
        org_id=x_edu_org_id or "default",
        role=role,
    )
    request.state.edu_actor = actor
    return actor


def has_permission(actor: ActorContext, permission: str) -> bool:
    allowed = ROLE_PERMISSIONS.get(actor.role, set())
    return "*" in allowed or permission in allowed


def require_permission_dep(permission: str):
    async def _dep(actor: ActorContext = Depends(get_actor_context)):
        if not has_permission(actor, permission):
            raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
        return actor

    _dep.__name__ = f"permission_{permission.replace(':', '_')}"
    return _dep


def permission_matrix_for_role(role: OrgRole) -> PermissionMatrix:
    return PermissionMatrix(role=role, permissions=sorted(ROLE_PERMISSIONS.get(role, set())))
