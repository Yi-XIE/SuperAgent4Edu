import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createProject,
  createResource,
  createRun,
  createStudentTask,
  createTemplate,
  loadEducationWorkbenchData,
  publishTemplate,
  updateTemplate,
} from "./api";

export function useEducationWorkbench() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["education", "workbench"],
    queryFn: () => loadEducationWorkbenchData(),
  });

  return {
    data:
      data ??
      ({
        actor: null,
        orgs: [],
        projects: [],
        runs: [],
        templates: [],
        resources: [],
        tasks: [],
        submissions: [],
        auditLogs: [],
      } as const),
    isLoading,
    error,
    refetch,
  };
}

export function useEducationActions() {
  const queryClient = useQueryClient();

  async function invalidate() {
    await queryClient.invalidateQueries({
      queryKey: ["education", "workbench"],
    });
  }

  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => void invalidate(),
  });

  const createRunMutation = useMutation({
    mutationFn: createRun,
    onSuccess: () => void invalidate(),
  });

  const createTemplateMutation = useMutation({
    mutationFn: createTemplate,
    onSuccess: () => void invalidate(),
  });

  const updateTemplateMutation = useMutation({
    mutationFn: ({
      templateId,
      payload,
    }: {
      templateId: string;
      payload: Parameters<typeof updateTemplate>[1];
    }) => updateTemplate(templateId, payload),
    onSuccess: () => void invalidate(),
  });

  const publishTemplateMutation = useMutation({
    mutationFn: publishTemplate,
    onSuccess: () => void invalidate(),
  });

  const createResourceMutation = useMutation({
    mutationFn: createResource,
    onSuccess: () => void invalidate(),
  });

  const createStudentTaskMutation = useMutation({
    mutationFn: createStudentTask,
    onSuccess: () => void invalidate(),
  });

  return {
    createProject: createProjectMutation,
    createRun: createRunMutation,
    createTemplate: createTemplateMutation,
    updateTemplate: updateTemplateMutation,
    publishTemplate: publishTemplateMutation,
    createResource: createResourceMutation,
    createStudentTask: createStudentTaskMutation,
  };
}
