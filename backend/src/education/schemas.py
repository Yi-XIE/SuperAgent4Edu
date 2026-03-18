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

GenerationMode = Literal["from_scratch", "material_first", "mixed"]
CriticPolicy = Literal["manual_on", "manual_off", "auto"]
StageStatus = Literal["pending", "running", "completed", "failed"]
BootstrapStatus = Literal["pending", "ready", "failed"]
AssetExtractionStatus = Literal[
    "pending",
    "ready_for_confirmation",
    "confirmed",
    "skipped",
]
TeachingAssetType = Literal[
    "goal_fragment",
    "driving_question",
    "activity_idea",
    "learning_kit_plan",
    "reference_note",
    "expression_template",
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
    checkpoint_id: Literal[
        "cp1-task-confirmation",
        "cp2-goal-lock",
        "cp3-draft-review",
        "cp4-asset-extraction-confirm",
    ]
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
    thread_id: str | None = None
    bootstrap_status: BootstrapStatus = "pending"
    bootstrap_at: str | None = None
    agent_name: str = "education-course-studio"
    generation_mode: GenerationMode = "mixed"
    critic_enabled: bool = False
    critic_policy: CriticPolicy = "manual_off"
    critic_activation_reason: str | None = None
    status: Literal["running", "awaiting_checkpoint", "rework", "accepted", "closed"] = "running"
    current_stage: str = "Stage 0"
    blueprint_status: StageStatus = "pending"
    package_status: StageStatus = "pending"
    asset_extraction_status: AssetExtractionStatus = "pending"
    workflow_template_id: str | None = None
    asset_retrieval_notes: list[str] = Field(default_factory=list)
    selected_asset_ids: list[str] = Field(default_factory=list)
    retrieval_snapshot_at: str | None = None
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
    start_chat: bool = False
    generation_mode: GenerationMode = "mixed"
    critic_enabled: bool | None = None
    critic_policy: CriticPolicy | None = None
    workflow_template_id: str | None = None


class UpdateRunRequest(BaseModel):
    status: Literal["running", "awaiting_checkpoint", "rework", "accepted", "closed"] | None = None
    current_stage: str | None = None
    thread_id: str | None = None
    bootstrap_status: BootstrapStatus | None = None
    bootstrap_at: str | None = None
    generation_mode: GenerationMode | None = None
    critic_enabled: bool | None = None
    critic_policy: CriticPolicy | None = None
    critic_activation_reason: str | None = None
    blueprint_status: StageStatus | None = None
    package_status: StageStatus | None = None
    asset_extraction_status: AssetExtractionStatus | None = None
    workflow_template_id: str | None = None
    asset_retrieval_notes: list[str] | None = None
    selected_asset_ids: list[str] | None = None
    retrieval_snapshot_at: str | None = None
    rerun_targets: list[str] | None = None
    artifact_paths: list[str] | None = None


class CheckpointDecision(BaseModel):
    checkpoint_id: Literal[
        "cp1-task-confirmation",
        "cp2-goal-lock",
        "cp3-draft-review",
        "cp4-asset-extraction-confirm",
    ]
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


class CourseBlueprint(BaseModel):
    id: str
    org_id: str
    run_id: str
    title: str
    big_ideas: list[str] = Field(default_factory=list)
    essential_questions: list[str] = Field(default_factory=list)
    transfer_goals: list[str] = Field(default_factory=list)
    project_direction: str = ""
    research_summary: str = ""
    source_brief_path: str = "/mnt/user-data/workspace/course-brief.json"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateCourseBlueprintRequest(BaseModel):
    org_id: str
    run_id: str
    title: str
    big_ideas: list[str] = Field(default_factory=list)
    essential_questions: list[str] = Field(default_factory=list)
    transfer_goals: list[str] = Field(default_factory=list)
    project_direction: str = ""
    research_summary: str = ""
    source_brief_path: str = "/mnt/user-data/workspace/course-brief.json"


class CoursePackage(BaseModel):
    id: str
    org_id: str
    run_id: str
    blueprint_id: str | None = None
    summary: str = ""
    lesson_plan_path: str = "/mnt/user-data/outputs/lesson-plan.md"
    ppt_outline_path: str = "/mnt/user-data/outputs/ppt-outline.md"
    learning_kit_path: str = "/mnt/user-data/outputs/learning-kit-appendix.md"
    reference_summary_path: str = "/mnt/user-data/outputs/reference-summary.md"
    artifact_manifest_path: str = "/mnt/user-data/outputs/artifact-manifest.json"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateCoursePackageRequest(BaseModel):
    org_id: str
    run_id: str
    blueprint_id: str | None = None
    summary: str = ""
    lesson_plan_path: str = "/mnt/user-data/outputs/lesson-plan.md"
    ppt_outline_path: str = "/mnt/user-data/outputs/ppt-outline.md"
    learning_kit_path: str = "/mnt/user-data/outputs/learning-kit-appendix.md"
    reference_summary_path: str = "/mnt/user-data/outputs/reference-summary.md"
    artifact_manifest_path: str = "/mnt/user-data/outputs/artifact-manifest.json"


class TeachingAsset(BaseModel):
    id: str
    org_id: str
    asset_type: TeachingAssetType
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    grade_band: str = "elementary"
    domain_focus: list[str] = Field(default_factory=list)
    source_run_id: str | None = None
    source_path: str | None = None
    confidence: float = 0.0
    usage_count: int = 0
    visibility: Literal["private", "org_shared"] = "private"
    status: Literal["active", "archived"] = "active"
    created_by: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class CreateTeachingAssetRequest(BaseModel):
    org_id: str
    asset_type: TeachingAssetType
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    grade_band: str = "elementary"
    domain_focus: list[str] = Field(default_factory=list)
    source_run_id: str | None = None
    source_path: str | None = None
    confidence: float = 0.0
    visibility: Literal["private", "org_shared"] = "private"


class UpdateTeachingAssetRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    grade_band: str | None = None
    domain_focus: list[str] | None = None
    confidence: float | None = None
    usage_count: int | None = None
    visibility: Literal["private", "org_shared"] | None = None
    status: Literal["active", "archived"] | None = None


class AssetExtractionCandidate(BaseModel):
    id: str
    org_id: str
    run_id: str
    asset_type: TeachingAssetType
    title: str
    content: str
    source_path: str = ""
    suggested_tags: list[str] = Field(default_factory=list)
    suggested_visibility: Literal["private", "org_shared"] = "private"
    status: Literal["candidate", "accepted", "skipped"] = "candidate"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class AssetExtractionCandidateInput(BaseModel):
    id: str | None = None
    asset_type: TeachingAssetType
    title: str
    content: str
    source_path: str = ""
    suggested_tags: list[str] = Field(default_factory=list)
    suggested_visibility: Literal["private", "org_shared"] = "private"


class UpsertExtractionRequest(BaseModel):
    mode: Literal["upsert", "confirm"] = "upsert"
    option: Literal["一键入库", "跳过本轮", "调整分类后入库"] | None = None
    selected_ids: list[str] = Field(default_factory=list)
    classifications: dict[str, list[str]] = Field(default_factory=dict)
    candidates: list[AssetExtractionCandidateInput] = Field(default_factory=list)


class TeachingFeedback(BaseModel):
    id: str
    org_id: str
    run_id: str
    user_id: str
    used_sections: list[str] = Field(default_factory=list)
    changed_sections: list[str] = Field(default_factory=list)
    ineffective_sections: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    summary: str = ""
    rating: float | None = None
    source: Literal["manual", "student_review"] = "manual"
    submission_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class CreateTeachingFeedbackRequest(BaseModel):
    org_id: str
    run_id: str
    used_sections: list[str] = Field(default_factory=list)
    changed_sections: list[str] = Field(default_factory=list)
    ineffective_sections: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    summary: str = ""
    rating: float | None = None
    source: Literal["manual", "student_review"] = "manual"
    submission_id: str | None = None


class MemorySignalUsage(BaseModel):
    category: str
    content: str
    confidence: float = 0.0
    source: str = "memory_injection"
    used_at: str = Field(default_factory=utc_now_iso)


class EducationRunResult(BaseModel):
    run: EducationRunState
    blueprint: CourseBlueprint | None = None
    package: CoursePackage | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    parse_errors: list[str] = Field(default_factory=list)
    extraction_candidates: list[AssetExtractionCandidate] = Field(default_factory=list)
    extracted_assets: list[TeachingAsset] = Field(default_factory=list)
    retrieval_basis: list[str] = Field(default_factory=list)


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
