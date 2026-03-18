"""Pydantic models for education platform APIs."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


OrgRole = Literal[
    "platform_admin",
    "org_admin",
    "curriculum_lead",
    "teacher",
    "reviewer",
    "student",
]


class PermissionMatrix(BaseModel):
    role: OrgRole
    permissions: list[str] = Field(default_factory=list)


class ActorContext(BaseModel):
    user_id: str
    org_id: str
    role: OrgRole


class OrgMember(BaseModel):
    user_id: str
    role: OrgRole
    joined_at: str = Field(default_factory=utc_now_iso)
    active: bool = True


class Org(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    members: list[OrgMember] = Field(default_factory=list)


class CreateOrgRequest(BaseModel):
    name: str
    description: str = ""


class AddOrgMemberRequest(BaseModel):
    user_id: str
    role: OrgRole


class EducationProject(BaseModel):
    id: str
    org_id: str
    name: str
    description: str = ""
    owner_id: str
    status: Literal["draft", "active", "archived"] = "draft"
    version: int = 1
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateProjectRequest(BaseModel):
    org_id: str
    name: str
    description: str = ""


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: Literal["draft", "active", "archived"] | None = None


class ReviewerHardGateV2(BaseModel):
    name: str
    status: Literal["pass", "fail", "na"]
    note: str = ""


class ReviewerRubricScoreV2(BaseModel):
    dimension: str
    is_hard_gate: bool = False
    score: int = Field(ge=0, le=3)
    status: Literal["pass", "fail", "na"] | None = None
    note: str = ""


class ReviewerSummaryV2(BaseModel):
    verdict: Literal["通过", "有条件通过", "不通过"]
    hard_gates: list[ReviewerHardGateV2] = Field(default_factory=list)
    key_issues: list[str] = Field(default_factory=list)
    rubric_scores: list[ReviewerRubricScoreV2] = Field(default_factory=list)
    suggested_rerun_agents: list[str] = Field(default_factory=list)
    lead_note: str = ""


class CriticSummaryV2(BaseModel):
    verdict: Literal["同意", "部分同意", "不同意"]
    agreement_with_reviewer: Literal["same", "partial", "conflict"]
    new_key_risks: list[str] = Field(default_factory=list)
    escalate_rerun: bool = False
    suggested_rerun_agents: list[str] = Field(default_factory=list)
    lead_note: str = ""


class RerunGuardState(BaseModel):
    draft_review_rework_count: int = 0
    max_local_rework: int = 1


class CheckpointHistoryItem(BaseModel):
    checkpoint_id: Literal["cp1-task-confirmation", "cp2-goal-lock", "cp3-draft-review"]
    raw_option: str
    normalized_option: str
    actor_user_id: str
    decided_at: str = Field(default_factory=utc_now_iso)
    rerun_targets: list[str] = Field(default_factory=list)
    reopened_to_cp1: bool = False


class EducationRunState(BaseModel):
    id: str
    org_id: str
    project_id: str
    title: str
    agent_name: str = "education-course-studio"
    status: Literal["running", "awaiting_checkpoint", "rework", "accepted", "closed"] = "running"
    current_stage: str = "Stage 0"
    guard: RerunGuardState = Field(default_factory=RerunGuardState)
    checkpoint_history: list[CheckpointHistoryItem] = Field(default_factory=list)
    rerun_targets: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    retry_target: str | None = None
    details: str | None = None
    reviewer_summary: ReviewerSummaryV2 | None = None
    critic_summary: CriticSummaryV2 | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateRunRequest(BaseModel):
    org_id: str
    project_id: str
    title: str
    current_stage: str = "Stage 0"


class UpdateRunRequest(BaseModel):
    status: Literal["running", "awaiting_checkpoint", "rework", "accepted", "closed"] | None = None
    current_stage: str | None = None
    rerun_targets: list[str] | None = None
    artifact_paths: list[str] | None = None


class CheckpointDecision(BaseModel):
    checkpoint_id: Literal["cp1-task-confirmation", "cp2-goal-lock", "cp3-draft-review"]
    option: str
    actor_user_id: str | None = None


class CheckpointDecisionResult(BaseModel):
    run: EducationRunState
    normalized_option: str
    rerun_targets: list[str] = Field(default_factory=list)
    reopened_to_cp1: bool = False
    recommended_option: str | None = None
    retry_target: str | None = None
    details: str | None = None


class EducationTemplate(BaseModel):
    id: str
    org_id: str
    type: Literal["course", "workflow", "review"]
    name: str
    description: str = ""
    content: dict = Field(default_factory=dict)
    version: int = 1
    status: Literal["draft", "published"] = "draft"
    created_by: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateTemplateRequest(BaseModel):
    org_id: str
    type: Literal["course", "workflow", "review"]
    name: str
    description: str = ""
    content: dict = Field(default_factory=dict)


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: dict | None = None
    status: Literal["draft", "published"] | None = None


class EducationResource(BaseModel):
    id: str
    org_id: str
    title: str
    url: str
    source_type: Literal["article", "video", "paper", "policy", "dataset", "other"] = "other"
    tags: list[str] = Field(default_factory=list)
    whitelisted: bool = True
    summary: str = ""
    created_by: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateResourceRequest(BaseModel):
    org_id: str
    title: str
    url: str
    source_type: Literal["article", "video", "paper", "policy", "dataset", "other"] = "other"
    tags: list[str] = Field(default_factory=list)
    whitelisted: bool = True
    summary: str = ""


class UpdateResourceRequest(BaseModel):
    title: str | None = None
    url: str | None = None
    source_type: Literal["article", "video", "paper", "policy", "dataset", "other"] | None = None
    tags: list[str] | None = None
    whitelisted: bool | None = None
    summary: str | None = None


class StudentTask(BaseModel):
    id: str
    org_id: str
    project_id: str
    run_id: str
    title: str
    description: str
    assigned_to: list[str] = Field(default_factory=list)
    due_at: str | None = None
    created_by: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateStudentTaskRequest(BaseModel):
    org_id: str
    project_id: str
    run_id: str
    title: str
    description: str
    assigned_to: list[str] = Field(default_factory=list)
    due_at: str | None = None


class StudentSubmission(BaseModel):
    id: str
    org_id: str
    task_id: str
    student_user_id: str
    content: str
    attachments: list[str] = Field(default_factory=list)
    score: float | None = None
    teacher_feedback: str | None = None
    submitted_at: str = Field(default_factory=utc_now_iso)
    reviewed_at: str | None = None


class SubmitStudentTaskRequest(BaseModel):
    org_id: str
    task_id: str
    content: str
    attachments: list[str] = Field(default_factory=list)


class ReviewSubmissionRequest(BaseModel):
    score: float | None = None
    teacher_feedback: str


class MemorySignalUsage(BaseModel):
    category: str
    content: str
    confidence: float = 0.0
    source: str = "memory_injection"
    used_at: str = Field(default_factory=utc_now_iso)


class AuditLogEntry(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: OrgRole
    action: str
    entity_type: str
    entity_id: str
    details: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
