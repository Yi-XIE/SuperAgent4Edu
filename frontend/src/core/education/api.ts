import { getBackendBaseURL } from "@/core/config";

import type {
  ActorContext,
  AuditLogEntry,
  EducationProject,
  EducationResource,
  EducationRunState,
  EducationTemplate,
  EducationWorkbenchData,
  Org,
  StudentSubmission,
  StudentTask,
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
  checkpoint_id: "cp1-task-confirmation" | "cp2-goal-lock" | "cp3-draft-review";
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
      }),
    },
  );
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

export async function loadEducationWorkbenchData(): Promise<EducationWorkbenchData> {
  const [actor, orgs, projects, templates, resources, tasks, submissions, auditLogs] =
    await Promise.all([
      getActorContext().catch(() => null),
      listOrgs().catch(() => []),
      listProjects().catch(() => []),
      listTemplates().catch(() => []),
      listResources().catch(() => []),
      listStudentTasks().catch(() => []),
      listStudentSubmissions().catch(() => []),
      listAuditLogs().catch(() => []),
    ]);

  const runsByProject = await Promise.all(
    projects.map((project) =>
      listProjectRuns(project.id).catch(() => [] as EducationRunState[]),
    ),
  );

  return {
    actor,
    orgs,
    projects,
    runs: runsByProject.flat(),
    templates,
    resources,
    tasks,
    submissions,
    auditLogs,
  };
}
