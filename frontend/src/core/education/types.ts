export interface EducationTaskBrief {
  course_topic: string;
  grade_band: "elementary";
  grade_or_level: string;
  domain_focus: Array<"ai-education" | "science-education" | "mixed">;
  session_count: number;
  session_length_minutes?: number;
  ubd_constraints: {
    big_ideas: string[];
    essential_questions: string[];
    transfer_goals: string[];
  };
  pbl_constraints: {
    driving_question: string;
    project_type: string;
    final_product: string;
  };
  learning_kit: {
    required: boolean;
    constraints: string[];
    school_fabrication_level: string;
    cost_bias: string;
  };
  teacher_notes: string;
}

export type EducationCheckpointType =
  | "task_confirmation"
  | "goal_lock"
  | "draft_review";

export interface EducationCheckpointOption {
  index: number;
  label: string;
  value: string;
}

export interface EducationCheckpoint {
  type: EducationCheckpointType;
  title: string;
  checkpoint_type?: string;
  context?: string;
  summary?: string;
  question: string;
  checkpoint_id?: string;
  recommended_option?: string;
  retry_target?: string;
  details?: string;
  options: EducationCheckpointOption[];
  rawContent: string;
}

export interface CourseArtifactManifestEntry {
  label: string;
  path: string;
  description?: string;
}

export interface CourseArtifactManifest {
  title: string;
  summary?: string;
  artifacts: CourseArtifactManifestEntry[];
}

export interface ReviewerHardGate {
  name: string;
  status: string;
  note?: string;
}

export interface ReviewerRubricScore {
  dimension: string;
  is_hard_gate?: boolean;
  score: number;
  status?: string;
  note?: string;
}

export interface ReviewerSummary {
  verdict: string;
  hard_gates: ReviewerHardGate[];
  key_issues: string[];
  rubric_scores: ReviewerRubricScore[];
  suggested_rerun_agents: string[];
  lead_note?: string;
}

export interface CriticSummary {
  verdict: string;
  agreement_with_reviewer: string;
  new_key_risks: string[];
  escalate_rerun?: boolean;
  suggested_rerun_agents: string[];
  lead_note?: string;
}

export interface EducationSubtaskMeta {
  stage: string;
  label: string;
}

export type EducationOrgRole =
  | "platform_admin"
  | "org_admin"
  | "curriculum_lead"
  | "teacher"
  | "reviewer"
  | "student";

export interface ActorContext {
  user_id: string;
  org_id: string;
  role: EducationOrgRole;
}

export interface OrgMember {
  user_id: string;
  role: EducationOrgRole;
  joined_at: string;
  active: boolean;
}

export interface Org {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  members: OrgMember[];
}

export interface EducationProject {
  id: string;
  org_id: string;
  name: string;
  description: string;
  owner_id: string;
  status: "draft" | "active" | "archived";
  version: number;
  created_at: string;
  updated_at: string;
}

export interface RerunGuardState {
  draft_review_rework_count: number;
  max_local_rework: number;
}

export interface CheckpointHistoryItem {
  checkpoint_id:
    | "cp1-task-confirmation"
    | "cp2-goal-lock"
    | "cp3-draft-review";
  raw_option: string;
  normalized_option: string;
  actor_user_id: string;
  decided_at: string;
  rerun_targets: string[];
  reopened_to_cp1: boolean;
}

export interface EducationRunState {
  id: string;
  org_id: string;
  project_id: string;
  title: string;
  agent_name: string;
  status: "running" | "awaiting_checkpoint" | "rework" | "accepted" | "closed";
  current_stage: string;
  guard: RerunGuardState;
  checkpoint_history: CheckpointHistoryItem[];
  rerun_targets: string[];
  recommended_option?: string | null;
  retry_target?: string | null;
  details?: string | null;
  reviewer_summary?: ReviewerSummary | null;
  critic_summary?: CriticSummary | null;
  artifact_paths: string[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface EducationTemplate {
  id: string;
  org_id: string;
  type: "course" | "workflow" | "review";
  name: string;
  description: string;
  content: Record<string, unknown>;
  version: number;
  status: "draft" | "published";
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface EducationResource {
  id: string;
  org_id: string;
  title: string;
  url: string;
  source_type: "article" | "video" | "paper" | "policy" | "dataset" | "other";
  tags: string[];
  whitelisted: boolean;
  summary: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface StudentTask {
  id: string;
  org_id: string;
  project_id: string;
  run_id: string;
  title: string;
  description: string;
  assigned_to: string[];
  due_at?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface StudentSubmission {
  id: string;
  org_id: string;
  task_id: string;
  student_user_id: string;
  content: string;
  attachments: string[];
  score?: number | null;
  teacher_feedback?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
}

export interface MemorySignalUsage {
  category: string;
  content: string;
  confidence: number;
  source: string;
  used_at: string;
}

export interface AuditLogEntry {
  id: string;
  org_id: string;
  user_id: string;
  role: EducationOrgRole;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface EducationWorkbenchData {
  actor: ActorContext | null;
  orgs: Org[];
  projects: EducationProject[];
  runs: EducationRunState[];
  templates: EducationTemplate[];
  resources: EducationResource[];
  tasks: StudentTask[];
  submissions: StudentSubmission[];
  auditLogs: AuditLogEntry[];
}
