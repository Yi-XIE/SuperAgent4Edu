"""Organization and membership APIs for education platform."""

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import get_actor_context, permission_matrix_for_role, require_permission_dep
from src.education.schemas import AddOrgMemberRequest, ActorContext, CreateOrgRequest, Org, OrgMember
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/orgs",
    tags=["orgs"],
    dependencies=[Depends(make_rate_limiter("orgs_api", 240))],
)


@router.get("", response_model=list[Org], summary="List organizations")
async def list_orgs(actor: ActorContext = Depends(require_permission_dep("org:read"))) -> list[Org]:
    store = get_education_store()
    state = store.read_state()
    orgs = [Org(**value) for value in state["orgs"].values() if isinstance(value, dict)]
    if actor.role == "platform_admin":
        return orgs
    return [org for org in orgs if org.id == actor.org_id]


@router.post("", response_model=Org, summary="Create organization")
async def create_org(
    payload: CreateOrgRequest,
    actor: ActorContext = Depends(require_permission_dep("org:write")),
) -> Org:
    store = get_education_store()
    org_id = store.generate_id("org")
    org = Org(id=org_id, name=payload.name, description=payload.description, members=[OrgMember(user_id=actor.user_id, role="org_admin")])

    def _mutate(state: dict):
        state["orgs"][org.id] = org.model_dump()
        return state["orgs"][org.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="org.create", entity_type="org", entity_id=org.id, details={"name": payload.name})
    return Org(**created)


@router.get("/{org_id}", response_model=Org, summary="Get organization")
async def get_org(org_id: str, actor: ActorContext = Depends(require_permission_dep("org:read"))) -> Org:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")
    store = get_education_store()
    state = store.read_state()
    raw = state["orgs"].get(org_id)
    if not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Organization not found")
    return Org(**raw)


@router.get("/{org_id}/members", response_model=list[OrgMember], summary="List organization members")
async def list_org_members(org_id: str, actor: ActorContext = Depends(require_permission_dep("org:read"))) -> list[OrgMember]:
    org = await get_org(org_id, actor)
    return org.members


@router.post("/{org_id}/members", response_model=OrgMember, summary="Add organization member")
async def add_org_member(
    org_id: str,
    payload: AddOrgMemberRequest,
    actor: ActorContext = Depends(require_permission_dep("member:write")),
) -> OrgMember:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")
    store = get_education_store()

    def _mutate(state: dict):
        org = state["orgs"].get(org_id)
        if not isinstance(org, dict):
            raise HTTPException(status_code=404, detail="Organization not found")
        members = org.setdefault("members", [])
        for member in members:
            if member.get("user_id") == payload.user_id:
                member["role"] = payload.role
                member["active"] = True
                return member
        item = OrgMember(user_id=payload.user_id, role=payload.role).model_dump()
        members.append(item)
        return item

    member = store.transaction(_mutate)
    write_audit_log(
        store,
        actor=actor,
        action="org.member.upsert",
        entity_type="org_member",
        entity_id=f"{org_id}:{payload.user_id}",
        details={"role": payload.role},
    )
    return OrgMember(**member)


@router.delete("/{org_id}/members/{user_id}", summary="Deactivate organization member")
async def remove_org_member(
    org_id: str,
    user_id: str,
    actor: ActorContext = Depends(require_permission_dep("member:write")),
) -> dict:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")
    store = get_education_store()

    def _mutate(state: dict):
        org = state["orgs"].get(org_id)
        if not isinstance(org, dict):
            raise HTTPException(status_code=404, detail="Organization not found")
        for member in org.get("members", []):
            if member.get("user_id") == user_id:
                member["active"] = False
                return {"ok": True}
        raise HTTPException(status_code=404, detail="Member not found")

    result = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="org.member.deactivate", entity_type="org_member", entity_id=f"{org_id}:{user_id}")
    return result


@router.get("/{org_id}/permissions/{role}", summary="Get permission matrix for role")
async def get_permission_matrix(
    org_id: str,
    role: str,
    actor: ActorContext = Depends(require_permission_dep("org:read")),
) -> dict:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")
    if role not in {"platform_admin", "org_admin", "curriculum_lead", "teacher", "reviewer", "student"}:
        raise HTTPException(status_code=400, detail="Unknown role")
    matrix = permission_matrix_for_role(role)  # type: ignore[arg-type]
    return matrix.model_dump()


@router.get("/me/context", response_model=ActorContext, summary="Get actor context")
async def get_actor(actor: ActorContext = Depends(get_actor_context)) -> ActorContext:
    return actor
