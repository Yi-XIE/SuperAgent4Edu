import { getBackendBaseURL } from "@/core/config";

import type {
  ActorContext,
  AssetExtractionCandidate,
  AuditLogEntry,
  CourseBlueprint,
  CoursePackage,
  EducationProject,
  EducationResource,
  EducationRunState,
  EducationRunResult,
  EducationTemplate,
  EducationWorkbenchData,
  GenerationMode,
  Org,
  StudentSubmission,
  StudentTask,
  TeachingAsset,
  TeachingAssetType,
  TeachingFeedback,
} from "./types";

async function educationFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${getBackendBaseURL()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new Error(detail.detail ?? `Education API error: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getActorContext(): Promise<ActorContext> {
  return educationFetch<ActorContext>("/api/orgs/me/context");
}

export async function listOrgs(): Promise<Org[]> {
  return educationFetch<Org[]>("/api/orgs");
}

export async function listProjects(): Promise<EducationProject[]> {
  return educationFetch<EducationProject[]>("/api/education/projects");
}

export async function listProjectRuns(
  projectId: string,
): Promise<EducationRunState[]> {
  return educationFetch<EducationRunState[]>(
    `/api/education/projects/${projectId}/runs`,
  );
}

export async function listTemplates(
  templateType?: "course" | "workflow" | "review",
): Promise<EducationTemplate[]> {
  const query = templateType
    ? `?template_type=${encodeURIComponent(templateType)}`
    : "";
  return educationFetch<EducationTemplate[]>(`/api/templates${query}`);
}

export async function listResources(): Promise<EducationResource[]> {
  return educationFetch<EducationResource[]>("/api/resources");
}

export async function listAssets(): Promise<TeachingAsset[]> {
  return educationFetch<TeachingAsset[]>("/api/education/assets");
}

export async function listBlueprints(
  runId?: string,
): Promise<CourseBlueprint[]> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return educationFetch<CourseBlueprint[]>(`/api/education/blueprints${query}`);
}

export async function listPackages(
  runId?: string,
): Promise<CoursePackage[]> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return educationFetch<CoursePackage[]>(`/api/education/packages${query}`);
}

export async function getRunResult(runId: string): Promise<EducationRunResult> {
  return educationFetch<EducationRunResult>(`/api/education/runs/${runId}/result`);
}

export async function listFeedback(runId?: string): Promise<TeachingFeedback[]> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return educationFetch<TeachingFeedback[]>(`/api/education/feedback${query}`);
}

export async function listExtractionCandidates(
  runId: string,
): Promise<AssetExtractionCandidate[]> {
  return educationFetch<AssetExtractionCandidate[]>(
    `/api/education/extractions/${runId}`,
  );
}

export async function listStudentTasks(): Promise<StudentTask[]> {
  return educationFetch<StudentTask[]>("/api/student/tasks");
}

export async function listStudentSubmissions(): Promise<StudentSubmission[]> {
  return educationFetch<StudentSubmission[]>("/api/student/submissions");
}

export async function listAuditLogs(): Promise<AuditLogEntry[]> {
  return educationFetch<AuditLogEntry[]>("/api/education/audit?limit=60");
}

export async function decideCheckpoint(payload: {
  run_id: string;
  checkpoint_id:
    | "cp1-task-confirmation"
    | "cp2-goal-lock"
    | "cp3-draft-review"
    | "cp4-asset-extraction-confirm";
  option: string;
  actor_user_id?: string;
}): Promise<EducationRunState> {
  const result = await educationFetch<{
    run: EducationRunState;
  }>(`/api/education/checkpoints/${payload.run_id}/decide`, {
    method: "POST",
    body: JSON.stringify({
      checkpoint_id: payload.checkpoint_id,
      option: payload.option,
      actor_user_id: payload.actor_user_id,
    }),
  });
  return result.run;
}

export async function createProject(payload: {
  org_id: string;
  name: string;
  description?: string;
}): Promise<EducationProject> {
  return educationFetch<EducationProject>("/api/education/projects", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      name: payload.name,
      description: payload.description ?? "",
    }),
  });
}

export async function createRun(payload: {
  project_id: string;
  org_id: string;
  title: string;
  start_chat?: boolean;
  generation_mode?: GenerationMode;
  critic_enabled?: boolean;
  critic_policy?: "manual_on" | "manual_off" | "auto";
  workflow_template_id?: string | null;
}): Promise<EducationRunState> {
  return educationFetch<EducationRunState>(
    `/api/education/projects/${payload.project_id}/runs`,
    {
      method: "POST",
      body: JSON.stringify({
        project_id: payload.project_id,
        org_id: payload.org_id,
        title: payload.title,
        current_stage: "Stage 0",
        start_chat: payload.start_chat ?? false,
        generation_mode: payload.generation_mode ?? "mixed",
        critic_enabled: payload.critic_enabled ?? false,
        critic_policy:
          payload.critic_policy ??
          ((payload.critic_enabled ?? false) ? "manual_on" : "manual_off"),
        workflow_template_id: payload.workflow_template_id ?? null,
      }),
    },
  );
}

export async function bootstrapRun(runId: string): Promise<EducationRunState> {
  return educationFetch<EducationRunState>(`/api/education/runs/${runId}/bootstrap`, {
    method: "POST",
  });
}

export async function updateRun(
  runId: string,
  payload: {
    status?: "running" | "awaiting_checkpoint" | "rework" | "accepted" | "closed";
    current_stage?: string;
    thread_id?: string | null;
    bootstrap_status?: "pending" | "ready" | "failed";
    bootstrap_at?: string | null;
    generation_mode?: GenerationMode;
    critic_enabled?: boolean;
    critic_policy?: "manual_on" | "manual_off" | "auto";
    critic_activation_reason?: string | null;
    blueprint_status?: "pending" | "running" | "completed" | "failed";
    package_status?: "pending" | "running" | "completed" | "failed";
    asset_extraction_status?:
      | "pending"
      | "ready_for_confirmation"
      | "confirmed"
      | "skipped";
    workflow_template_id?: string | null;
    asset_retrieval_notes?: string[];
    selected_asset_ids?: string[];
    retrieval_snapshot_at?: string | null;
    rerun_targets?: string[];
    artifact_paths?: string[];
  },
): Promise<EducationRunState> {
  return educationFetch<EducationRunState>(`/api/education/runs/${runId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function createTemplate(payload: {
  org_id: string;
  type: "course" | "workflow" | "review";
  name: string;
  description?: string;
  content?: Record<string, unknown>;
}): Promise<EducationTemplate> {
  return educationFetch<EducationTemplate>("/api/templates", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      type: payload.type,
      name: payload.name,
      description: payload.description ?? "",
      content: payload.content ?? {},
    }),
  });
}

export async function updateTemplate(
  templateId: string,
  payload: {
    name?: string;
    description?: string;
    content?: Record<string, unknown>;
    status?: "draft" | "published";
  },
): Promise<EducationTemplate> {
  return educationFetch<EducationTemplate>(`/api/templates/${templateId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function publishTemplate(
  templateId: string,
): Promise<EducationTemplate> {
  return educationFetch<EducationTemplate>(`/api/templates/${templateId}/publish`, {
    method: "POST",
  });
}

export async function createResource(payload: {
  org_id: string;
  title: string;
  url: string;
  source_type?: "article" | "video" | "paper" | "policy" | "dataset" | "other";
  tags?: string[];
  whitelisted?: boolean;
  summary?: string;
}): Promise<EducationResource> {
  return educationFetch<EducationResource>("/api/resources", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      title: payload.title,
      url: payload.url,
      source_type: payload.source_type ?? "other",
      tags: payload.tags ?? [],
      whitelisted: payload.whitelisted ?? true,
      summary: payload.summary ?? "",
    }),
  });
}

export async function createAsset(payload: {
  org_id: string;
  asset_type: TeachingAssetType;
  title: string;
  content: string;
  tags?: string[];
  source_run_id?: string | null;
  source_path?: string | null;
  visibility?: "private" | "org_shared";
}): Promise<TeachingAsset> {
  return educationFetch<TeachingAsset>("/api/education/assets", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      asset_type: payload.asset_type,
      title: payload.title,
      content: payload.content,
      tags: payload.tags ?? [],
      source_run_id: payload.source_run_id ?? null,
      source_path: payload.source_path ?? null,
      visibility: payload.visibility ?? "private",
    }),
  });
}

export async function updateAsset(
  assetId: string,
  payload: {
    title?: string;
    content?: string;
    tags?: string[];
    confidence?: number;
    usage_count?: number;
    visibility?: "private" | "org_shared";
    status?: "active" | "archived";
  },
): Promise<TeachingAsset> {
  return educationFetch<TeachingAsset>(`/api/education/assets/${assetId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function upsertOrConfirmExtraction(
  runId: string,
  payload: {
    mode?: "upsert" | "confirm";
    option?: "一键入库" | "跳过本轮" | "调整分类后入库";
    selected_ids?: string[];
    classifications?: Record<string, string[]>;
    candidates?: Array<{
      id?: string;
      asset_type: TeachingAssetType;
      title: string;
      content: string;
      source_path?: string;
      suggested_tags?: string[];
      suggested_visibility?: "private" | "org_shared";
    }>;
  },
): Promise<AssetExtractionCandidate[]> {
  return educationFetch<AssetExtractionCandidate[]>(
    `/api/education/extractions/${runId}`,
    {
      method: "POST",
      body: JSON.stringify({
        mode: payload.mode ?? "upsert",
        option: payload.option,
        selected_ids: payload.selected_ids ?? [],
        classifications: payload.classifications ?? {},
        candidates: payload.candidates ?? [],
      }),
    },
  );
}

export async function createStudentTask(payload: {
  org_id: string;
  project_id: string;
  run_id: string;
  title: string;
  description: string;
  assigned_to?: string[];
}): Promise<StudentTask> {
  return educationFetch<StudentTask>("/api/student/tasks", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      project_id: payload.project_id,
      run_id: payload.run_id,
      title: payload.title,
      description: payload.description,
      assigned_to: payload.assigned_to ?? [],
    }),
  });
}

export async function createFeedback(payload: {
  org_id: string;
  run_id: string;
  used_sections?: string[];
  changed_sections?: string[];
  ineffective_sections?: string[];
  asset_ids?: string[];
  summary?: string;
  rating?: number | null;
  source?: "manual" | "student_review";
  submission_id?: string | null;
}): Promise<TeachingFeedback> {
  return educationFetch<TeachingFeedback>("/api/education/feedback", {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      run_id: payload.run_id,
      used_sections: payload.used_sections ?? [],
      changed_sections: payload.changed_sections ?? [],
      ineffective_sections: payload.ineffective_sections ?? [],
      asset_ids: payload.asset_ids ?? [],
      summary: payload.summary ?? "",
      rating: payload.rating ?? null,
      source: payload.source ?? "manual",
      submission_id: payload.submission_id ?? null,
    }),
  });
}

export async function submitStudentTask(
  taskId: string,
  payload: {
    org_id: string;
    content: string;
    attachments?: string[];
  },
): Promise<StudentSubmission> {
  return educationFetch<StudentSubmission>(`/api/student/tasks/${taskId}/submit`, {
    method: "POST",
    body: JSON.stringify({
      org_id: payload.org_id,
      task_id: taskId,
      content: payload.content,
      attachments: payload.attachments ?? [],
    }),
  });
}

export async function reviewStudentSubmission(
  submissionId: string,
  payload: {
    score?: number | null;
    teacher_feedback: string;
  },
): Promise<StudentSubmission> {
  return educationFetch<StudentSubmission>(
    `/api/student/submissions/${submissionId}/review`,
    {
      method: "PATCH",
      body: JSON.stringify({
        score: payload.score ?? null,
        teacher_feedback: payload.teacher_feedback,
      }),
    },
  );
}

export async function loadEducationWorkbenchData(): Promise<EducationWorkbenchData> {
  const [
    actor,
    orgs,
    projects,
    assets,
    templates,
    resources,
    tasks,
    submissions,
    feedback,
    auditLogs,
  ] =
    await Promise.all([
      getActorContext().catch(() => null),
      listOrgs().catch(() => []),
      listProjects().catch(() => []),
      listAssets().catch(() => []),
      listTemplates().catch(() => []),
      listResources().catch(() => []),
      listStudentTasks().catch(() => []),
      listStudentSubmissions().catch(() => []),
      listFeedback().catch(() => []),
      listAuditLogs().catch(() => []),
    ]);

  const runsByProject = await Promise.all(
    projects.map((project) =>
      listProjectRuns(project.id).catch(() => [] as EducationRunState[]),
    ),
  );
  const runs = runsByProject.flat();
  const runResultRows = await Promise.all(
    runs.map((run) => getRunResult(run.id).catch(() => null)),
  );
  const runResults: Record<string, EducationRunResult> = {};
  for (const row of runResultRows) {
    if (!row) {
      continue;
    }
    runResults[row.run.id] = row;
  }

  return {
    actor,
    orgs,
    projects,
    runs,
    runResults,
    assets,
    templates,
    resources,
    tasks,
    submissions,
    feedback,
    auditLogs,
  };
}
