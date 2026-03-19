"use client";

import Link from "next/link";
import { BookOpenIcon, FolderOpenIcon, SparklesIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EducationResource, EducationRunState, TeachingAsset } from "@/core/education";

export function EducationRunSidebar({
  currentRunId,
  runs,
  assets,
  resources,
}: {
  currentRunId: string;
  runs: EducationRunState[];
  assets: TeachingAsset[];
  resources: EducationResource[];
}) {
  const recentRuns = runs.slice(0, 6);
  const recentAssets = assets.slice(0, 4);
  const recentResources = resources.slice(0, 4);

  return (
    <aside className="hidden w-80 shrink-0 flex-col gap-4 xl:flex">
      <Card>
        <CardHeader className="gap-3">
          <CardTitle className="text-base">备课导航</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button asChild className="w-full justify-start">
            <Link href="/workspace/education">
              <SparklesIcon className="h-4 w-4" />
              返回教育 Hub
            </Link>
          </Button>
          <Button asChild className="w-full justify-start" variant="outline">
            <Link href="/workspace/education/templates">
              <FolderOpenIcon className="h-4 w-4" />
              查看模板与工作流
            </Link>
          </Button>
          <Button asChild className="w-full justify-start" variant="outline">
            <Link href="/workspace/education/resources">
              <BookOpenIcon className="h-4 w-4" />
              打开资源库
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">最近课包</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {recentRuns.map((run) => (
            <Link
              key={run.id}
              className="hover:border-primary/50 block rounded-lg border p-3 transition-colors"
              href={`/workspace/education/runs/${run.id}`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="line-clamp-1 text-sm font-medium">{run.title}</p>
                {run.id === currentRunId && <Badge>当前</Badge>}
              </div>
              <p className="text-muted-foreground mt-1 text-xs">
                {run.current_stage} | {run.status}
              </p>
            </Link>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">素材台快捷入口</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {recentAssets.length === 0 && (
            <p className="text-muted-foreground text-xs">暂无素材</p>
          )}
          {recentAssets.map((asset) => (
            <div key={asset.id} className="rounded-lg border p-3">
              <p className="line-clamp-1 text-sm font-medium">{asset.title}</p>
              <p className="text-muted-foreground mt-1 text-xs">
                {asset.asset_type}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">资源库快捷入口</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {recentResources.length === 0 && (
            <p className="text-muted-foreground text-xs">暂无资源</p>
          )}
          {recentResources.map((resource) => (
            <div key={resource.id} className="rounded-lg border p-3">
              <p className="line-clamp-1 text-sm font-medium">{resource.title}</p>
              <p className="text-muted-foreground mt-1 text-xs">
                {resource.source_type}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </aside>
  );
}
