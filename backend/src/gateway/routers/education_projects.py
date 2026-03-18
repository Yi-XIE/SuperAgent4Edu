"""Education project APIs."""

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException

from src.education.audit import write_audit_log
from src.education.bootstrap import bootstrap_run_state
from src.education.rate_limit import make_rate_limiter
from src.education.rbac import require_permission_dep
from src.education.schemas import (
    ActorContext,
    CreateProjectRequest,
    CreateRunRequest,
    EducationProject,
    EducationRunState,
    UpdateProjectRequest,
)
from src.education.store import get_education_store

router = APIRouter(
    prefix="/api/education/projects",
    tags=["education"],
    dependencies=[Depends(make_rate_limiter("education_projects_api", 240))],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard_org(actor: ActorContext, org_id: str) -> None:
    if actor.role != "platform_admin" and actor.org_id != org_id:
        raise HTTPException(status_code=403, detail="Cross-org access denied")


@router.get("", response_model=list[EducationProject], summary="List education projects")
async def list_projects(actor: ActorContext = Depends(require_permission_dep("project:read"))) -> list[EducationProject]:
    store = get_education_store()
    state = store.read_state()
    projects = [EducationProject(**row) for row in state["projects"].values() if isinstance(row, dict)]
    if actor.role == "platform_admin":
        return projects
    return [project for project in projects if project.org_id == actor.org_id]


@router.post("", response_model=EducationProject, summary="Create education project")
async def create_project(
    payload: CreateProjectRequest,
    actor: ActorContext = Depends(require_permission_dep("project:write")),
) -> EducationProject:
    _guard_org(actor, payload.org_id)
    store = get_education_store()
    project = EducationProject(
        id=store.generate_id("proj"),
        org_id=payload.org_id,
        name=payload.name,
        description=payload.description,
        owner_id=actor.user_id,
    )

    def _mutate(state: dict):
        state["projects"][project.id] = project.model_dump()
        return state["projects"][project.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="project.create", entity_type="project", entity_id=project.id)
    return EducationProject(**created)


@router.get("/{project_id}", response_model=EducationProject, summary="Get education project")
async def get_project(project_id: str, actor: ActorContext = Depends(require_permission_dep("project:read"))) -> EducationProject:
    store = get_education_store()
    state = store.read_state()
    raw = state["projects"].get(project_id)
    if not isinstance(raw, dict):
        raise HTTPException(status_code=404, detail="Project not found")
    project = EducationProject(**raw)
    _guard_org(actor, project.org_id)
    return project


@router.patch("/{project_id}", response_model=EducationProject, summary="Update education project")
async def update_project(
    project_id: str,
    payload: UpdateProjectRequest,
    actor: ActorContext = Depends(require_permission_dep("project:write")),
) -> EducationProject:
    store = get_education_store()

    def _mutate(state: dict):
        raw = state["projects"].get(project_id)
        if not isinstance(raw, dict):
            raise HTTPException(status_code=404, detail="Project not found")
        project = EducationProject(**raw)
        _guard_org(actor, project.org_id)
        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description
        if payload.status is not None:
            project.status = payload.status
        project.version += 1
        project.updated_at = _now()
        state["projects"][project_id] = project.model_dump()
        return state["projects"][project_id]

    updated = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="project.update", entity_type="project", entity_id=project_id)
    return EducationProject(**updated)


@router.get("/{project_id}/runs", response_model=list[EducationRunState], summary="List project runs")
async def list_project_runs(
    project_id: str,
    actor: ActorContext = Depends(require_permission_dep("run:read")),
) -> list[EducationRunState]:
    project = await get_project(project_id, actor)
    store = get_education_store()
    state = store.read_state()
    runs = [EducationRunState(**row) for row in state["runs"].values() if isinstance(row, dict)]
    return [run for run in runs if run.project_id == project.id]


@router.post("/{project_id}/runs", response_model=EducationRunState, summary="Create run under project")
async def create_project_run(
    project_id: str,
    payload: CreateRunRequest,
    actor: ActorContext = Depends(require_permission_dep("run:write")),
) -> EducationRunState:
    project = await get_project(project_id, actor)
    if payload.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id mismatch between path and payload")
    if payload.org_id != project.org_id:
        raise HTTPException(status_code=400, detail="org_id mismatch with project")
    store = get_education_store()
    run = EducationRunState(
        id=store.generate_id("run"),
        org_id=project.org_id,
        project_id=project.id,
        title=payload.title,
        thread_id=str(uuid.uuid4()) if payload.start_chat else None,
        bootstrap_status="pending",
        current_stage=payload.current_stage,
        generation_mode=payload.generation_mode,
        critic_enabled=bool(payload.critic_enabled) if payload.critic_enabled is not None else False,
        critic_policy=(
            payload.critic_policy
            if payload.critic_policy is not None
            else (
                "manual_on"
                if bool(payload.critic_enabled) is True
                else "manual_off"
            )
        ),
        workflow_template_id=payload.workflow_template_id,
        blueprint_status="pending",
        package_status="pending",
        asset_extraction_status="pending",
    )
    if run.critic_policy == "manual_on":
        run.critic_enabled = True
    elif run.critic_policy == "manual_off":
        run.critic_enabled = False

    def _mutate(state: dict):
        bootstrap_run_state(state, run)
        state["runs"][run.id] = run.model_dump()
        return state["runs"][run.id]

    created = store.transaction(_mutate)
    write_audit_log(store, actor=actor, action="run.create", entity_type="run", entity_id=run.id, details={"project_id": project.id})
    return EducationRunState(**created)
