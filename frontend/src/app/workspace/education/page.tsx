"use client";

import {
  ActivityIcon,
  BookOpenCheckIcon,
  FolderKanbanIcon,
  GraduationCapIcon,
  NetworkIcon,
  PackageIcon,
  ShieldCheckIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, startTransition } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { EducationWorkflowBuilder } from "@/components/workspace/education-workflow-builder";
import { useEducationActions, useEducationWorkbench } from "@/core/education";
import { useI18n } from "@/core/i18n/hooks";

function timeLabel(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export default function EducationWorkbenchPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { data, isLoading, error, refetch } = useEducationWorkbench();
  const actions = useEducationActions();

  const [workflowTemplateId, setWorkflowTemplateId] = useState<string | null>(
    null,
  );
  const [workflowContent, setWorkflowContent] = useState<string>("{}");
  const [newTemplateName, setNewTemplateName] = useState<string>("");
  const [newResourceTitle, setNewResourceTitle] = useState<string>("");
  const [newResourceUrl, setNewResourceUrl] = useState<string>("");
  const [newAssetTitle, setNewAssetTitle] = useState<string>("");
  const [newAssetContent, setNewAssetContent] = useState<string>("");
  const [studentAssignee, setStudentAssignee] = useState<string>("student-001");
  const [studentTaskRunId, setStudentTaskRunId] = useState<string>("");
  const [selectedSubmitTaskId, setSelectedSubmitTaskId] = useState<string>("");
  const [studentSubmitContent, setStudentSubmitContent] = useState<string>("");
  const [selectedReviewSubmissionId, setSelectedReviewSubmissionId] = useState<string>("");
  const [reviewScore, setReviewScore] = useState<string>("");
  const [reviewComment, setReviewComment] = useState<string>("");
  const [feedbackSummary, setFeedbackSummary] = useState<string>("");
  const [feedbackRating, setFeedbackRating] = useState<string>("");

  useEffect(() => {
    document.title = `Education Workbench - ${t.pages.appName}`;
  }, [t.pages.appName]);

  const orgId = data.actor?.org_id ?? data.orgs[0]?.id ?? "default";
  const projects = data.projects;
  const runs = data.runs;
  const runResults = data.runResults;
  const assets = data.assets;
  const templates = data.templates;
  const resources = data.resources;
  const tasks = data.tasks;
  const submissions = data.submissions;
  const feedback = data.feedback;
  const auditLogs = data.auditLogs;

  const workflowTemplates = useMemo(
    () => templates.filter((item) => item.type === "workflow"),
    [templates],
  );
  const acceptedRuns = useMemo(
    () => runs.filter((run) => run.status === "accepted"),
    [runs],
  );

  useEffect(() => {
    if (workflowTemplates.length === 0) {
      setWorkflowTemplateId(null);
      setWorkflowContent("{}");
      return;
    }
    const selected =
      workflowTemplates.find((item) => item.id === workflowTemplateId) ??
      workflowTemplates[0];
    if (!selected) {
      return;
    }
    setWorkflowTemplateId(selected.id);
    setWorkflowContent(JSON.stringify(selected.content ?? {}, null, 2));
  }, [workflowTemplateId, workflowTemplates]);

  const selectedWorkflowTemplate = useMemo(
    () =>
      workflowTemplateId
        ? workflowTemplates.find((item) => item.id === workflowTemplateId) ??
          null
        : null,
    [workflowTemplateId, workflowTemplates],
  );

  useEffect(() => {
    if (tasks.length === 0) {
      if (selectedSubmitTaskId) {
        setSelectedSubmitTaskId("");
      }
      return;
    }
    if (!selectedSubmitTaskId || !tasks.some((task) => task.id === selectedSubmitTaskId)) {
      setSelectedSubmitTaskId(tasks[0]?.id ?? "");
    }
  }, [selectedSubmitTaskId, tasks]);

  useEffect(() => {
    if (submissions.length === 0) {
      if (selectedReviewSubmissionId) {
        setSelectedReviewSubmissionId("");
      }
      return;
    }
    if (
      !selectedReviewSubmissionId ||
      !submissions.some((submission) => submission.id === selectedReviewSubmissionId)
    ) {
      setSelectedReviewSubmissionId(submissions[0]?.id ?? "");
    }
  }, [selectedReviewSubmissionId, submissions]);

  useEffect(() => {
    if (acceptedRuns.length === 0) {
      if (studentTaskRunId) {
        setStudentTaskRunId("");
      }
      return;
    }
    if (
      !studentTaskRunId ||
      !acceptedRuns.some((run) => run.id === studentTaskRunId)
    ) {
      setStudentTaskRunId(acceptedRuns[0]?.id ?? "");
    }
  }, [acceptedRuns, studentTaskRunId]);

  async function bootstrapProjectAndRun() {
    try {
      const project = await actions.createProject.mutateAsync({
        org_id: orgId,
        name: `课程项目 ${new Date().toLocaleDateString()}`,
        description: "教师课程工作台自动创建的演示项目",
      });
      await actions.createRun.mutateAsync({
        project_id: project.id,
        org_id: project.org_id,
        title: `课程运行 ${new Date().toLocaleTimeString()}`,
        start_chat: true,
      });
      toast.success("已创建项目与运行");
    } catch (createError) {
      toast.error(
        createError instanceof Error
          ? createError.message
          : "创建项目失败",
      );
    }
  }

  async function createWorkflowTemplate() {
    if (!newTemplateName.trim()) {
      toast.error("请先输入模板名称");
      return;
    }
    try {
      await actions.createTemplate.mutateAsync({
        org_id: orgId,
        type: "workflow",
        name: newTemplateName.trim(),
        description: "工作流编辑器创建",
        content: {
          nodes: [
            "Presentation",
            "Reviewer",
            "Critic",
            "Checkpoint3",
            "PresentFiles",
          ],
          rerun_guard: "max_local_rework=1",
        },
      });
      setNewTemplateName("");
      toast.success("工作流模板已创建");
    } catch (createError) {
      toast.error(
        createError instanceof Error
          ? createError.message
          : "创建模板失败",
      );
    }
  }

  async function saveWorkflowTemplate() {
    if (!selectedWorkflowTemplate) {
      toast.error("暂无可编辑的工作流模板");
      return;
    }
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(workflowContent) as Record<string, unknown>;
    } catch {
      toast.error("工作流 JSON 格式不正确");
      return;
    }

    try {
      await actions.updateTemplate.mutateAsync({
        templateId: selectedWorkflowTemplate.id,
        payload: {
          content: parsed,
        },
      });
      toast.success("工作流模板已保存");
    } catch (saveError) {
      toast.error(
        saveError instanceof Error ? saveError.message : "保存模板失败",
      );
    }
  }

  async function publishSelectedWorkflowTemplate() {
    if (!selectedWorkflowTemplate) {
      toast.error("暂无可发布的工作流模板");
      return;
    }
    try {
      await actions.publishTemplate.mutateAsync(selectedWorkflowTemplate.id);
      toast.success("工作流模板已发布");
    } catch (publishError) {
      toast.error(
        publishError instanceof Error
          ? publishError.message
          : "发布模板失败",
      );
    }
  }

  async function bindWorkflowTemplateToLatestRun() {
    const run = runs[0];
    if (!run) {
      toast.error("请先创建课程运行");
      return;
    }
    if (!selectedWorkflowTemplate) {
      toast.error("请先选择工作流模板");
      return;
    }
    try {
      await actions.updateRun.mutateAsync({
        runId: run.id,
        payload: {
          workflow_template_id: selectedWorkflowTemplate.id,
        },
      });
      toast.success("已绑定到最近课程运行");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "绑定失败");
    }
  }

  async function createResourceQuickly() {
    if (!newResourceTitle.trim() || !newResourceUrl.trim()) {
      toast.error("请填写资源标题和链接");
      return;
    }
    try {
      await actions.createResource.mutateAsync({
        org_id: orgId,
        title: newResourceTitle.trim(),
        url: newResourceUrl.trim(),
        source_type: "article",
        tags: ["UbD", "PBL"],
        whitelisted: true,
      });
      setNewResourceTitle("");
      setNewResourceUrl("");
      toast.success("资源已入库");
    } catch (createError) {
      toast.error(
        createError instanceof Error ? createError.message : "资源创建失败",
      );
    }
  }

  async function createAssetQuickly() {
    if (!newAssetTitle.trim() || !newAssetContent.trim()) {
      toast.error("请填写素材标题和内容");
      return;
    }
    const run = runs[0] ?? null;
    try {
      await actions.createAsset.mutateAsync({
        org_id: orgId,
        asset_type: "activity_idea",
        title: newAssetTitle.trim(),
        content: newAssetContent.trim(),
        tags: ["课堂可复用"],
        source_run_id: run?.id ?? null,
        visibility: "private",
      });
      setNewAssetTitle("");
      setNewAssetContent("");
      toast.success("素材已保存");
    } catch (createError) {
      toast.error(
        createError instanceof Error ? createError.message : "素材创建失败",
      );
    }
  }

  async function createFeedbackQuickly() {
    const run = runs[0];
    if (!run) {
      toast.error("请先创建课程运行");
      return;
    }
    try {
      const parsedRating =
        feedbackRating.trim().length > 0 ? Number(feedbackRating.trim()) : null;
      await actions.createFeedback.mutateAsync({
        org_id: run.org_id,
        run_id: run.id,
        summary: feedbackSummary.trim() || "课堂反馈记录",
        rating:
          parsedRating !== null && Number.isFinite(parsedRating)
            ? parsedRating
            : null,
      });
      setFeedbackSummary("");
      setFeedbackRating("");
      toast.success("反馈已写入");
    } catch (createError) {
      toast.error(
        createError instanceof Error ? createError.message : "写入反馈失败",
      );
    }
  }

  async function confirmExtractionQuickly(option: "一键入库" | "跳过本轮") {
    const run = runs[0];
    if (!run) {
      toast.error("请先创建课程运行");
      return;
    }
    try {
      await actions.upsertOrConfirmExtraction.mutateAsync({
        runId: run.id,
        payload: {
          mode: "confirm",
          option,
        },
      });
      toast.success(option === "一键入库" ? "素材候选已入库" : "已跳过本轮素材沉淀");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "素材确认失败");
    }
  }

  async function createStudentTaskQuickly() {
    const run =
      acceptedRuns.find((item) => item.id === studentTaskRunId) ??
      acceptedRuns[0];
    if (!run) {
      toast.error("请先让课程运行通过验收（accepted）");
      return;
    }
    try {
      await actions.createStudentTask.mutateAsync({
        org_id: run.org_id,
        project_id: run.project_id,
        run_id: run.id,
        title: `学生任务 ${new Date().toLocaleTimeString()}`,
        description: "根据本次课程草案完成项目作品与反思日志。",
        assigned_to: [studentAssignee.trim() || "student-001"],
      });
      toast.success("学生任务已发布");
    } catch (createError) {
      toast.error(
        createError instanceof Error ? createError.message : "发布学生任务失败",
      );
    }
  }

  function openRunChat(runId: string, threadId?: string | null) {
    const encodedRunId = encodeURIComponent(runId);
    if (threadId) {
      router.push(
        `/workspace/agents/education-course-studio/chats/${threadId}?run_id=${encodedRunId}`,
      );
      return;
    }
    router.push(
      `/workspace/agents/education-course-studio/chats/new?run_id=${encodedRunId}`,
    );
  }

  async function submitStudentTaskQuickly() {
    if (!selectedSubmitTaskId.trim()) {
      toast.error("请先选择任务");
      return;
    }
    if (!studentSubmitContent.trim()) {
      toast.error("请填写学生提交内容");
      return;
    }
    const task = tasks.find((item) => item.id === selectedSubmitTaskId.trim());
    if (!task) {
      toast.error("任务不存在");
      return;
    }
    try {
      await actions.submitStudentTask.mutateAsync({
        taskId: task.id,
        payload: {
          org_id: task.org_id,
          content: studentSubmitContent.trim(),
        },
      });
      setStudentSubmitContent("");
      toast.success("学生提交已写入");
    } catch (submitError) {
      toast.error(
        submitError instanceof Error ? submitError.message : "学生提交失败",
      );
    }
  }

  async function reviewSubmissionQuickly() {
    if (!selectedReviewSubmissionId.trim()) {
      toast.error("请先选择提交");
      return;
    }
    if (!reviewComment.trim()) {
      toast.error("请填写评阅意见");
      return;
    }
    const submission = submissions.find(
      (item) => item.id === selectedReviewSubmissionId.trim(),
    );
    if (!submission) {
      toast.error("提交不存在");
      return;
    }
    try {
      const parsedScore =
        reviewScore.trim().length > 0 ? Number(reviewScore.trim()) : null;
      await actions.reviewStudentSubmission.mutateAsync({
        submissionId: submission.id,
        payload: {
          score:
            parsedScore !== null && Number.isFinite(parsedScore)
              ? parsedScore
              : null,
          teacher_feedback: reviewComment.trim(),
        },
      });
      setReviewScore("");
      setReviewComment("");
      toast.success("评阅已完成，并已回流到教师反馈");
    } catch (reviewError) {
      toast.error(reviewError instanceof Error ? reviewError.message : "评阅失败");
    }
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody className="items-start p-6">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <FolderKanbanIcon className="h-4 w-4" />
                  项目与运行
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>项目数：{projects.length}</p>
                <p>运行数：{runs.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <NetworkIcon className="h-4 w-4" />
                  模板与工作流
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>模板数：{templates.length}</p>
                <p>工作流模板：{workflowTemplates.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <PackageIcon className="h-4 w-4" />
                  资源与学具
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>资源条目：{resources.length}</p>
                <p>素材条目：{assets.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <GraduationCapIcon className="h-4 w-4" />
                  学生任务链路
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>任务数：{tasks.length}</p>
                <p>提交数：{submissions.length}</p>
                <p>反馈数：{feedback.length}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheckIcon className="h-4 w-4" />
                快速引导
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button
                disabled={actions.createProject.isPending || actions.createRun.isPending}
                onClick={() => {
                  startTransition(() => {
                    void bootstrapProjectAndRun();
                  });
                }}
              >
                创建演示项目与运行
              </Button>
              <Button
                variant="outline"
                disabled={isLoading}
                onClick={() => {
                  void refetch();
                }}
              >
                刷新数据
              </Button>
              <Badge variant="secondary">
                当前身份：{data.actor?.role ?? "unknown"}
              </Badge>
              <Badge variant="secondary">
                当前组织：{orgId}
              </Badge>
            </CardContent>
          </Card>

          <Tabs defaultValue="teacher">
            <TabsList variant="line">
              <TabsTrigger value="teacher">教师工作台</TabsTrigger>
              <TabsTrigger value="workflow">工作流编辑器</TabsTrigger>
              <TabsTrigger value="templates">模板市场</TabsTrigger>
              <TabsTrigger value="assets">素材台</TabsTrigger>
              <TabsTrigger value="resources">资源库</TabsTrigger>
              <TabsTrigger value="student">学生端</TabsTrigger>
              <TabsTrigger value="audit">审计治理</TabsTrigger>
            </TabsList>

            <TabsContent value="teacher" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <BookOpenCheckIcon className="h-4 w-4" />
                    课程运行与审批历史
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {runs.length === 0 && (
                    <p className="text-muted-foreground text-sm">
                      暂无运行记录，点击上方“创建演示项目与运行”开始。
                    </p>
                  )}
                  {runs.map((run) => (
                    <div key={run.id} className="space-y-2 rounded border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{run.title}</p>
                        <Badge variant="outline">{run.status}</Badge>
                        <Badge variant="secondary">{run.current_stage}</Badge>
                        <Badge variant="secondary">{run.generation_mode}</Badge>
                        <Badge variant={run.critic_enabled ? "default" : "outline"}>
                          {run.critic_enabled ? "Critic 开启" : "Critic 关闭"}
                        </Badge>
                        <Badge variant="outline">
                          policy: {run.critic_policy}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-xs">
                        run_id: {run.id} | 更新时间：{timeLabel(run.updated_at)}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        thread_id: {run.thread_id ?? "-"} | bootstrap:{" "}
                        {run.bootstrap_status ?? "pending"}
                      </p>
                      {run.critic_activation_reason && (
                        <p className="text-muted-foreground text-xs">
                          Critic 原因：{run.critic_activation_reason}
                        </p>
                      )}
                      <p className="text-muted-foreground text-xs">
                        返工计数：{run.guard.draft_review_rework_count}/
                        {run.guard.max_local_rework}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        预召回快照：{timeLabel(run.retrieval_snapshot_at)}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {run.rerun_targets.map((target) => (
                          <Badge key={`${run.id}-${target}`} variant="secondary">
                            {target}
                          </Badge>
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">
                          Blueprint: {run.blueprint_status}
                        </Badge>
                        <Badge variant="outline">Package: {run.package_status}</Badge>
                        <Badge variant="outline">
                          Extraction: {run.asset_extraction_status}
                        </Badge>
                      </div>
                      {run.asset_retrieval_notes.length > 0 && (
                        <p className="text-muted-foreground text-xs">
                          素材召回：{run.asset_retrieval_notes.slice(0, 2).join("；")}
                        </p>
                      )}
                      <div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openRunChat(run.id, run.thread_id)}
                        >
                          进入关联聊天
                        </Button>
                      </div>
                      <div className="space-y-1">
                        {run.checkpoint_history.slice(-4).map((item) => (
                          <p
                            key={`${run.id}-${item.decided_at}-${item.raw_option}`}
                            className="text-muted-foreground text-xs"
                          >
                            {item.checkpoint_id}: {item.normalized_option} (
                            {timeLabel(item.decided_at)})
                          </p>
                        ))}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">课程结果区（对象化视图）</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {runs.length === 0 && (
                    <p className="text-muted-foreground text-sm">暂无可展示结果</p>
                  )}
                  {runs.map((run) => {
                    const result = runResults[run.id];
                    return (
                      <div key={`${run.id}-result`} className="space-y-2 rounded border p-3">
                        <p className="text-sm font-medium">
                          {run.title} · 结果聚合
                        </p>
                        {!result && (
                          <p className="text-muted-foreground text-xs">
                            结果尚未生成，刷新后重试。
                          </p>
                        )}
                        {result?.blueprint && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium">课程蓝图</p>
                            <p className="text-muted-foreground text-xs">
                              {result.blueprint.title}
                            </p>
                            {result.blueprint.big_ideas.length > 0 && (
                              <p className="text-muted-foreground text-xs">
                                Big Ideas：{result.blueprint.big_ideas.slice(0, 3).join("；")}
                              </p>
                            )}
                            {result.blueprint.essential_questions.length > 0 && (
                              <p className="text-muted-foreground text-xs">
                                Essential Questions：
                                {result.blueprint.essential_questions
                                  .slice(0, 2)
                                  .join("；")}
                              </p>
                            )}
                          </div>
                        )}
                        {result?.package && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium">课程包</p>
                            <p className="text-muted-foreground text-xs">
                              {result.package.summary || "暂无课包摘要"}
                            </p>
                          </div>
                        )}
                        {result && result.artifact_paths.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium">关键工件</p>
                            <div className="flex flex-wrap gap-2">
                              {result.artifact_paths.map((path) => (
                                <Badge key={`${run.id}-${path}`} variant="secondary">
                                  {path.split("/").slice(-1)[0]}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {result && result.retrieval_basis.length > 0 && (
                          <p className="text-muted-foreground text-xs">
                            召回依据：{result.retrieval_basis.slice(0, 2).join("；")}
                          </p>
                        )}
                        {result && result.extracted_assets.length > 0 && (
                          <p className="text-muted-foreground text-xs">
                            已沉淀素材：{result.extracted_assets.length} 条
                          </p>
                        )}
                        {result && result.parse_errors.length > 0 && (
                          <p className="text-muted-foreground text-xs">
                            解析告警：{result.parse_errors.slice(0, 2).join("；")}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="workflow" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">创建工作流模板</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-3">
                  <Input
                    className="max-w-sm"
                    placeholder="模板名称"
                    value={newTemplateName}
                    onChange={(event) => setNewTemplateName(event.target.value)}
                  />
                  <Button
                    disabled={actions.createTemplate.isPending}
                    onClick={() => {
                      startTransition(() => {
                        void createWorkflowTemplate();
                      });
                    }}
                  >
                    新建模板
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">工作流 JSON 编辑</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {workflowTemplates.map((template) => (
                      <Button
                        key={template.id}
                        variant={
                          workflowTemplateId === template.id
                            ? "default"
                            : "outline"
                        }
                        onClick={() => setWorkflowTemplateId(template.id)}
                      >
                        {template.name}
                      </Button>
                    ))}
                  </div>
                  <EducationWorkflowBuilder
                    value={workflowContent}
                    onChange={setWorkflowContent}
                  />
                  <p className="text-muted-foreground text-xs">
                    高级模式：可直接编辑 JSON（拖拽编排器会同步这些字段）。
                  </p>
                  <Textarea
                    className="min-h-[280px] font-mono text-xs"
                    value={workflowContent}
                    onChange={(event) => setWorkflowContent(event.target.value)}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={
                        actions.updateTemplate.isPending ||
                        selectedWorkflowTemplate === null
                      }
                      onClick={() => {
                        startTransition(() => {
                          void saveWorkflowTemplate();
                        });
                      }}
                    >
                      保存草稿
                    </Button>
                    <Button
                      variant="outline"
                      disabled={
                        actions.publishTemplate.isPending ||
                        selectedWorkflowTemplate === null
                      }
                      onClick={() => {
                        startTransition(() => {
                          void publishSelectedWorkflowTemplate();
                        });
                      }}
                    >
                      发布模板
                    </Button>
                    <Button
                      variant="outline"
                      disabled={
                        actions.updateRun.isPending ||
                        selectedWorkflowTemplate === null ||
                        runs.length === 0
                      }
                      onClick={() => {
                        startTransition(() => {
                          void bindWorkflowTemplateToLatestRun();
                        });
                      }}
                    >
                      绑定到最近运行
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="templates" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">模板市场</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {templates.length === 0 && (
                    <p className="text-muted-foreground text-sm">暂无模板</p>
                  )}
                  {templates.map((template) => (
                    <div
                      key={template.id}
                      className="flex flex-wrap items-center gap-2 rounded border p-3 text-sm"
                    >
                      <Badge>{template.type}</Badge>
                      <span className="font-medium">{template.name}</span>
                      <Badge variant="outline">{template.status}</Badge>
                      <span className="text-muted-foreground text-xs">
                        v{template.version} | {timeLabel(template.updated_at)}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="assets" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">新增素材</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Input
                    placeholder="素材标题"
                    value={newAssetTitle}
                    onChange={(event) => setNewAssetTitle(event.target.value)}
                  />
                  <Textarea
                    placeholder="素材内容（可复用课堂片段）"
                    value={newAssetContent}
                    onChange={(event) => setNewAssetContent(event.target.value)}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={actions.createAsset.isPending}
                      onClick={() => {
                        startTransition(() => {
                          void createAssetQuickly();
                        });
                      }}
                    >
                      保存素材
                    </Button>
                    <Button
                      variant="outline"
                      disabled={actions.upsertOrConfirmExtraction.isPending}
                      onClick={() => {
                        startTransition(() => {
                          void confirmExtractionQuickly("一键入库");
                        });
                      }}
                    >
                      执行一键入库
                    </Button>
                    <Button
                      variant="outline"
                      disabled={actions.upsertOrConfirmExtraction.isPending}
                      onClick={() => {
                        startTransition(() => {
                          void confirmExtractionQuickly("跳过本轮");
                        });
                      }}
                    >
                      跳过本轮沉淀
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">教师素材台</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {assets.length === 0 && (
                    <p className="text-muted-foreground text-sm">暂无素材</p>
                  )}
                  {assets.map((asset) => (
                    <div key={asset.id} className="space-y-1 rounded border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge>{asset.asset_type}</Badge>
                        <span className="font-medium">{asset.title}</span>
                        <Badge variant="outline">{asset.visibility}</Badge>
                        <Badge variant="secondary">
                          复用 {asset.usage_count}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-xs">{asset.content}</p>
                      {asset.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {asset.tags.map((tag) => (
                            <Badge key={`${asset.id}-${tag}`} variant="secondary">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="resources" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">新增资源</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-3">
                  <Input
                    className="max-w-xs"
                    placeholder="资源标题"
                    value={newResourceTitle}
                    onChange={(event) => setNewResourceTitle(event.target.value)}
                  />
                  <Input
                    className="max-w-sm"
                    placeholder="https://..."
                    value={newResourceUrl}
                    onChange={(event) => setNewResourceUrl(event.target.value)}
                  />
                  <Button
                    disabled={actions.createResource.isPending}
                    onClick={() => {
                      startTransition(() => {
                        void createResourceQuickly();
                      });
                    }}
                  >
                    入库
                  </Button>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">组织资源库</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {resources.length === 0 && (
                    <p className="text-muted-foreground text-sm">暂无资源条目</p>
                  )}
                  {resources.map((resource) => (
                    <div key={resource.id} className="space-y-1 rounded border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{resource.title}</span>
                        <Badge variant="outline">{resource.source_type}</Badge>
                        <Badge variant="secondary">
                          {resource.whitelisted ? "白名单" : "未白名单"}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-xs">{resource.url}</p>
                      {resource.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {resource.tags.map((tag) => (
                            <Badge key={`${resource.id}-${tag}`} variant="secondary">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="student" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">发布学生任务</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-3">
                  <Select
                    value={studentTaskRunId}
                    onValueChange={setStudentTaskRunId}
                    disabled={acceptedRuns.length === 0}
                  >
                    <SelectTrigger className="max-w-sm">
                      <SelectValue placeholder="选择课程运行" />
                    </SelectTrigger>
                    <SelectContent>
                      {acceptedRuns.map((run) => (
                        <SelectItem key={run.id} value={run.id}>
                          {run.title} ({run.id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    className="max-w-xs"
                    placeholder="student-001"
                    value={studentAssignee}
                    onChange={(event) => setStudentAssignee(event.target.value)}
                  />
                  <Button
                    disabled={
                      actions.createStudentTask.isPending ||
                      acceptedRuns.length === 0
                    }
                    onClick={() => {
                      startTransition(() => {
                        void createStudentTaskQuickly();
                      });
                    }}
                  >
                    从课程运行创建任务
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">学生提交</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Select
                    value={selectedSubmitTaskId}
                    onValueChange={setSelectedSubmitTaskId}
                    disabled={tasks.length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择要提交的任务" />
                    </SelectTrigger>
                    <SelectContent>
                      {tasks.map((task) => (
                        <SelectItem key={task.id} value={task.id}>
                          {task.title} ({task.id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Textarea
                    placeholder="学生提交内容"
                    value={studentSubmitContent}
                    onChange={(event) => setStudentSubmitContent(event.target.value)}
                  />
                  <Button
                    disabled={actions.submitStudentTask.isPending}
                    onClick={() => {
                      startTransition(() => {
                        void submitStudentTaskQuickly();
                      });
                    }}
                  >
                    写入学生提交
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">教师评阅提交</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Select
                    value={selectedReviewSubmissionId}
                    onValueChange={setSelectedReviewSubmissionId}
                    disabled={submissions.length === 0}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择需要评阅的提交" />
                    </SelectTrigger>
                    <SelectContent>
                      {submissions.map((submission) => (
                        <SelectItem key={submission.id} value={submission.id}>
                          {submission.student_user_id}
                          {" -> "}
                          {submission.task_id} ({submission.id})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    placeholder="评分（可选）"
                    value={reviewScore}
                    onChange={(event) => setReviewScore(event.target.value)}
                  />
                  <Textarea
                    placeholder="评阅意见"
                    value={reviewComment}
                    onChange={(event) => setReviewComment(event.target.value)}
                  />
                  <Button
                    disabled={actions.reviewStudentSubmission.isPending}
                    onClick={() => {
                      startTransition(() => {
                        void reviewSubmissionQuickly();
                      });
                    }}
                  >
                    完成评阅并回流反馈
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">课堂反馈回流</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Textarea
                    placeholder="填写本次课堂反馈摘要"
                    value={feedbackSummary}
                    onChange={(event) => setFeedbackSummary(event.target.value)}
                  />
                  <Input
                    placeholder="评分（可选，如 4.5）"
                    value={feedbackRating}
                    onChange={(event) => setFeedbackRating(event.target.value)}
                  />
                  <Button
                    disabled={actions.createFeedback.isPending}
                    onClick={() => {
                      startTransition(() => {
                        void createFeedbackQuickly();
                      });
                    }}
                  >
                    写入反馈
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">任务与提交</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <p className="text-sm font-medium">任务</p>
                    {tasks.length === 0 && (
                      <p className="text-muted-foreground text-sm">暂无任务</p>
                    )}
                    {tasks.map((task) => (
                      <div key={task.id} className="rounded border p-3 text-sm">
                        <p className="font-medium">{task.title}</p>
                        <p className="text-muted-foreground text-xs">
                          run_id: {task.run_id} | 指派:{" "}
                          {task.assigned_to.join(", ") || "-"}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">提交</p>
                    {submissions.length === 0 && (
                      <p className="text-muted-foreground text-sm">暂无提交</p>
                    )}
                    {submissions.map((submission) => (
                      <div
                        key={submission.id}
                        className="rounded border p-3 text-sm"
                      >
                        <p className="font-medium">
                          {submission.student_user_id}
                          {" -> "}
                          {submission.task_id}
                        </p>
                        <p className="text-muted-foreground text-xs">
                          评分：{submission.score ?? "-"} | 评阅时间：
                          {timeLabel(submission.reviewed_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">教师反馈</p>
                    {feedback.length === 0 && (
                      <p className="text-muted-foreground text-sm">暂无反馈</p>
                    )}
                    {feedback.map((item) => (
                      <div key={item.id} className="rounded border p-3 text-sm">
                        <p>{item.summary || "课堂反馈"}</p>
                        <div className="mt-1 flex flex-wrap gap-2">
                          <Badge variant="outline">
                            {item.source === "student_review"
                              ? "来源：学生评阅"
                              : "来源：手工反馈"}
                          </Badge>
                          {item.submission_id && (
                            <Badge variant="secondary">
                              submission: {item.submission_id}
                            </Badge>
                          )}
                        </div>
                        <p className="text-muted-foreground text-xs">
                          run_id: {item.run_id} | 评分: {item.rating ?? "-"}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="audit" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ActivityIcon className="h-4 w-4" />
                    审计日志（最近 60 条）
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {auditLogs.length === 0 && (
                    <p className="text-muted-foreground text-sm">暂无审计记录</p>
                  )}
                  {auditLogs.map((log) => (
                    <div key={log.id} className="rounded border p-3 text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">{log.action}</Badge>
                        <span>{log.entity_type}</span>
                        <span className="text-muted-foreground text-xs">
                          {log.entity_id}
                        </span>
                      </div>
                      <p className="text-muted-foreground mt-1 text-xs">
                        {log.user_id} ({log.role}) | {timeLabel(log.created_at)}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {(isLoading || error) && (
            <Card>
              <CardContent className="pt-6 text-sm">
                {isLoading && <p>正在加载教育工作台数据...</p>}
                {error && (
                  <p className="text-destructive">
                    读取教育数据失败：
                    {error instanceof Error ? error.message : "未知错误"}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
