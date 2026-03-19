"use client";

import {
  BookOpenCheckIcon,
  FolderKanbanIcon,
  ShieldCheckIcon,
  StickyNoteIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useMemo } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useEducationActions, useEducationWorkbench } from "@/core/education";

function timeLabel(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

type GardenTabKey = "packages" | "assets" | "resources" | "feedback";

export default function EducationHubPage() {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useEducationWorkbench();
  const actions = useEducationActions();

  const orgId = data.actor?.org_id ?? data.orgs[0]?.id ?? "default";
  const projects = data.projects;
  const runs = data.runs;
  const assets = data.assets;
  const resources = data.resources;
  const feedback = data.feedback;

  const recentRuns = useMemo(() => runs.slice(0, 12), [runs]);
  const recentAssets = useMemo(() => assets.slice(0, 12), [assets]);
  const recentResources = useMemo(() => resources.slice(0, 12), [resources]);
  const recentFeedback = useMemo(() => feedback.slice(0, 12), [feedback]);
  const defaultTab: GardenTabKey = "packages";

  async function createRunAndOpen() {
    try {
      const project =
        projects[0] ??
        (await actions.createProject.mutateAsync({
          org_id: orgId,
          name: `课程项目 ${new Date().toLocaleDateString()}`,
          description: "知识花园自动创建的备课项目",
        }));
      const run = await actions.createRun.mutateAsync({
        project_id: project.id,
        org_id: project.org_id,
        title: `新的备课任务 ${new Date().toLocaleTimeString()}`,
      });
      router.push(`/workspace/education/runs/${run.id}`);
    } catch (createError) {
      toast.error(
        createError instanceof Error ? createError.message : "创建备课任务失败",
      );
    }
  }

  return (
    <div className="flex size-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold">知识花园</h1>
          <p className="text-muted-foreground mt-0.5 text-sm">
            统一查看课包、素材、资源库和教学反馈。
          </p>
          <p className="text-muted-foreground mt-0.5 text-xs">
            组织 {orgId} · 项目 {projects.length} · 运行 {runs.length} · 素材{" "}
            {assets.length} · 资源 {resources.length}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            disabled={actions.createRun.isPending || actions.createProject.isPending}
            onClick={() => {
              startTransition(() => {
                void createRunAndOpen();
              });
            }}
          >
            新建备课任务
          </Button>
          <Button
            variant="outline"
            disabled={recentRuns.length === 0}
            onClick={() => {
              const run = recentRuns[0];
              if (run) {
                router.push(`/workspace/education/runs/${run.id}`);
              }
            }}
          >
            继续最近一次
          </Button>
          <Button
            variant="outline"
            disabled={isLoading}
            onClick={() => {
              void refetch();
            }}
          >
            刷新
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <Tabs defaultValue={defaultTab} className="w-full">
          <TabsList variant="line" className="flex h-auto w-full flex-wrap">
            <TabsTrigger value="packages">课包</TabsTrigger>
            <TabsTrigger value="assets">素材</TabsTrigger>
            <TabsTrigger value="resources">资源库</TabsTrigger>
            <TabsTrigger value="feedback">教学反馈</TabsTrigger>
          </TabsList>

          <TabsContent value="packages" className="mt-4">
            {recentRuns.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
                暂无备课任务，点击上方“新建备课任务”开始。
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recentRuns.map((run) => (
                  <Link key={run.id} href={`/workspace/education/runs/${run.id}`}>
                    <Card className="hover:border-primary/50 h-full transition-colors">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <FolderKanbanIcon className="h-4 w-4" />
                          {run.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline">{run.status}</Badge>
                          <Badge variant="secondary">{run.current_stage}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-2 text-xs">
                          更新时间：{timeLabel(run.updated_at)}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="assets" className="mt-4">
            {recentAssets.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
                暂无素材沉淀。
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recentAssets.map((asset) => (
                  <Link key={asset.id} href="/workspace/education/resources">
                    <Card className="hover:border-primary/50 h-full transition-colors">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <BookOpenCheckIcon className="h-4 w-4" />
                          {asset.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          <Badge>{asset.asset_type}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-2 line-clamp-3 text-sm">
                          {asset.content}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="resources" className="mt-4">
            {recentResources.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
                暂无资源条目。
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recentResources.map((resource) => (
                  <a
                    key={resource.id}
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Card className="hover:border-primary/50 h-full transition-colors">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <StickyNoteIcon className="h-4 w-4" />
                          {resource.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline">{resource.source_type}</Badge>
                        </div>
                        <p className="text-muted-foreground mt-2 line-clamp-3 text-sm">
                          {resource.summary ?? resource.url}
                        </p>
                      </CardContent>
                    </Card>
                  </a>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="feedback" className="mt-4">
            {recentFeedback.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
                暂无教学反馈。
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {recentFeedback.map((item) => (
                  <Link key={item.id} href="/workspace/education/students">
                    <Card className="hover:border-primary/50 h-full transition-colors">
                      <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-base">
                          <ShieldCheckIcon className="h-4 w-4" />
                          教学反馈
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline">
                            {item.source === "student_review" ? "学生评阅" : "手工反馈"}
                          </Badge>
                          {typeof item.rating === "number" && (
                            <Badge variant="secondary">评分 {item.rating}</Badge>
                          )}
                        </div>
                        <p className="mt-2 line-clamp-3 text-sm">
                          {item.summary ?? "课堂反馈"}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {(isLoading || error) && (
          <div className="mt-4 rounded-lg border p-4 text-sm">
            {isLoading && <p>正在加载知识花园数据...</p>}
            {error && (
              <p className="text-destructive">
                读取教育数据失败：
                {error instanceof Error ? error.message : "未知错误"}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
