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
import { useEffect, useMemo, useState, startTransition } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
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
  const { data, isLoading, error, refetch } = useEducationWorkbench();
  const actions = useEducationActions();

  const [workflowTemplateId, setWorkflowTemplateId] = useState<string | null>(
    null,
  );
  const [workflowContent, setWorkflowContent] = useState<string>("{}");
  const [newTemplateName, setNewTemplateName] = useState<string>("");
  const [newResourceTitle, setNewResourceTitle] = useState<string>("");
  const [newResourceUrl, setNewResourceUrl] = useState<string>("");
  const [studentAssignee, setStudentAssignee] = useState<string>("student-001");

  useEffect(() => {
    document.title = `Education Workbench - ${t.pages.appName}`;
  }, [t.pages.appName]);

  const orgId = data.actor?.org_id ?? data.orgs[0]?.id ?? "default";
  const projects = data.projects;
  const runs = data.runs;
  const templates = data.templates;
  const resources = data.resources;
  const tasks = data.tasks;
  const submissions = data.submissions;
  const auditLogs = data.auditLogs;

  const workflowTemplates = useMemo(
    () => templates.filter((item) => item.type === "workflow"),
    [templates],
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

  async function createStudentTaskQuickly() {
    const run = runs[0];
    if (!run) {
      toast.error("请先创建课程运行");
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
                <p>最近审计：{auditLogs.length}</p>
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
                      </div>
                      <p className="text-muted-foreground text-xs">
                        run_id: {run.id} | 更新时间：{timeLabel(run.updated_at)}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        返工计数：{run.guard.draft_review_rework_count}/
                        {run.guard.max_local_rework}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {run.rerun_targets.map((target) => (
                          <Badge key={`${run.id}-${target}`} variant="secondary">
                            {target}
                          </Badge>
                        ))}
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
                  <Input
                    className="max-w-xs"
                    placeholder="student-001"
                    value={studentAssignee}
                    onChange={(event) => setStudentAssignee(event.target.value)}
                  />
                  <Button
                    disabled={actions.createStudentTask.isPending}
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
