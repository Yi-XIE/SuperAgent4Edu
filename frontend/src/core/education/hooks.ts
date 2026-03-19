import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createAsset,
  createFeedback,
  createProject,
  createResource,
  createRun,
  reviewStudentSubmission,
  submitStudentTask,
  updateRun,
  createStudentTask,
  createTemplate,
  upsertOrConfirmExtraction,
  loadEducationWorkbenchData,
  publishTemplate,
  updateAsset,
  updateTemplate,
} from "./api";

export function useEducationWorkbench(enabled = true) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["education", "workbench"],
    queryFn: () => loadEducationWorkbenchData(),
    enabled,
  });

  return {
    data:
      data ??
      ({
        actor: null,
        orgs: [],
        projects: [],
        runs: [],
        runResults: {},
        assets: [],
        templates: [],
        resources: [],
        tasks: [],
        submissions: [],
        feedback: [],
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

  const updateRunMutation = useMutation({
    mutationFn: ({
      runId,
      payload,
    }: {
      runId: string;
      payload: Parameters<typeof updateRun>[1];
    }) => updateRun(runId, payload),
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

  const createAssetMutation = useMutation({
    mutationFn: createAsset,
    onSuccess: () => void invalidate(),
  });

  const updateAssetMutation = useMutation({
    mutationFn: ({
      assetId,
      payload,
    }: {
      assetId: string;
      payload: Parameters<typeof updateAsset>[1];
    }) => updateAsset(assetId, payload),
    onSuccess: () => void invalidate(),
  });

  const upsertOrConfirmExtractionMutation = useMutation({
    mutationFn: ({
      runId,
      payload,
    }: {
      runId: string;
      payload: Parameters<typeof upsertOrConfirmExtraction>[1];
    }) => upsertOrConfirmExtraction(runId, payload),
    onSuccess: () => void invalidate(),
  });

  const createStudentTaskMutation = useMutation({
    mutationFn: createStudentTask,
    onSuccess: () => void invalidate(),
  });

  const submitStudentTaskMutation = useMutation({
    mutationFn: ({
      taskId,
      payload,
    }: {
      taskId: string;
      payload: Parameters<typeof submitStudentTask>[1];
    }) => submitStudentTask(taskId, payload),
    onSuccess: () => void invalidate(),
  });

  const reviewStudentSubmissionMutation = useMutation({
    mutationFn: ({
      submissionId,
      payload,
    }: {
      submissionId: string;
      payload: Parameters<typeof reviewStudentSubmission>[1];
    }) => reviewStudentSubmission(submissionId, payload),
    onSuccess: () => void invalidate(),
  });

  const createFeedbackMutation = useMutation({
    mutationFn: createFeedback,
    onSuccess: () => void invalidate(),
  });

  return {
    createProject: createProjectMutation,
    createRun: createRunMutation,
    updateRun: updateRunMutation,
    createTemplate: createTemplateMutation,
    updateTemplate: updateTemplateMutation,
    publishTemplate: publishTemplateMutation,
    createResource: createResourceMutation,
    createAsset: createAssetMutation,
    updateAsset: updateAssetMutation,
    upsertOrConfirmExtraction: upsertOrConfirmExtractionMutation,
    createStudentTask: createStudentTaskMutation,
    submitStudentTask: submitStudentTaskMutation,
    reviewStudentSubmission: reviewStudentSubmissionMutation,
    createFeedback: createFeedbackMutation,
  };
}
