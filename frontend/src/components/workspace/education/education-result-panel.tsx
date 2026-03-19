"use client";

import { ExternalLinkIcon, PackageOpenIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { urlOfArtifact } from "@/core/artifacts/utils";
import { type EducationRunResult } from "@/core/education";

function ArtifactLink({
  label,
  path,
  threadId,
}: {
  label: string;
  path?: string | null;
  threadId?: string | null;
}) {
  if (!path || !threadId) {
    return (
      <div className="rounded-lg border p-3 text-sm">
        <p className="font-medium">{label}</p>
        <p className="text-muted-foreground mt-1 text-xs">暂无文件</p>
      </div>
    );
  }

  return (
    <a
      className="hover:border-primary/40 flex items-start justify-between gap-3 rounded-lg border p-3 transition-colors"
      href={urlOfArtifact({ filepath: path, threadId })}
      rel="noreferrer"
      target="_blank"
    >
      <div className="space-y-1">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-muted-foreground text-xs">{path}</p>
      </div>
      <ExternalLinkIcon className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
    </a>
  );
}

export function EducationResultPanel({
  result,
}: {
  result?: EducationRunResult | null;
}) {
  const threadId = result?.run.thread_id ?? null;

  return (
    <Card className="gap-4">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-full">
            <PackageOpenIcon className="text-primary h-5 w-5" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-base">课包结果区</CardTitle>
            <p className="text-muted-foreground text-sm">
              围绕当前这一次备课任务查看课程蓝图、完整课包和素材沉淀结果。
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="blueprint">
          <TabsList variant="line" className="flex-wrap">
            <TabsTrigger value="blueprint">课程蓝图</TabsTrigger>
            <TabsTrigger value="lesson-plan">教案</TabsTrigger>
            <TabsTrigger value="ppt">PPT</TabsTrigger>
            <TabsTrigger value="learning-kit">学具</TabsTrigger>
            <TabsTrigger value="references">参考资料</TabsTrigger>
            <TabsTrigger value="assets">本次提取素材</TabsTrigger>
          </TabsList>

          <TabsContent className="mt-4 space-y-3" value="blueprint">
            {!result?.blueprint && (
              <p className="text-muted-foreground text-sm">暂无课程蓝图结果</p>
            )}
            {result?.blueprint && (
              <div className="space-y-3">
                <div className="rounded-lg border p-3">
                  <p className="text-sm font-medium">{result.blueprint.title}</p>
                  <p className="text-muted-foreground mt-1 text-sm leading-6">
                    {result.blueprint.project_direction}
                  </p>
                </div>
                <div className="grid gap-3">
                  <div className="rounded-lg border p-3">
                    <p className="text-xs font-medium">大概念</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.blueprint.big_ideas.map((idea) => (
                        <Badge key={idea} variant="secondary">
                          {idea}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs font-medium">核心问题</p>
                    <div className="mt-2 space-y-2">
                      {result.blueprint.essential_questions.map((question) => (
                        <p key={question} className="text-sm leading-6">
                          {question}
                        </p>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs font-medium">研究支撑摘要</p>
                    <p className="mt-2 text-sm leading-6">
                      {result.blueprint.research_summary}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent className="mt-4 space-y-3" value="lesson-plan">
            <ArtifactLink
              label="教案初稿"
              path={result?.package?.lesson_plan_path}
              threadId={threadId}
            />
            {result?.package?.summary && (
              <div className="rounded-lg border p-3 text-sm leading-6">
                {result.package.summary}
              </div>
            )}
          </TabsContent>

          <TabsContent className="mt-4 space-y-3" value="ppt">
            <ArtifactLink
              label="PPT 大纲"
              path={result?.package?.ppt_outline_path}
              threadId={threadId}
            />
          </TabsContent>

          <TabsContent className="mt-4 space-y-3" value="learning-kit">
            <ArtifactLink
              label="学具附录"
              path={result?.package?.learning_kit_path}
              threadId={threadId}
            />
          </TabsContent>

          <TabsContent className="mt-4 space-y-3" value="references">
            <ArtifactLink
              label="参考资料摘要"
              path={result?.package?.reference_summary_path}
              threadId={threadId}
            />
            {result && result.retrieval_basis.length > 0 && (
              <div className="rounded-lg border p-3">
                <p className="text-xs font-medium">本轮召回依据</p>
                <div className="mt-2 space-y-2">
                  {result.retrieval_basis.map((item) => (
                    <p key={item} className="text-sm leading-6">
                      {item}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent className="mt-4 space-y-3" value="assets">
            {(!result?.extraction_candidates.length &&
              !result?.extracted_assets.length) && (
              <p className="text-muted-foreground text-sm">暂无素材沉淀结果</p>
            )}
            {result?.extracted_assets.map((asset) => (
              <div key={asset.id} className="rounded-lg border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{asset.asset_type}</Badge>
                  <span className="text-sm font-medium">{asset.title}</span>
                  <Badge variant="outline">{asset.visibility}</Badge>
                </div>
                <p className="text-muted-foreground mt-2 text-sm leading-6">
                  {asset.content}
                </p>
              </div>
            ))}
            {result?.extraction_candidates
              .filter((candidate) => candidate.status === "candidate")
              .map((candidate) => (
                <div key={candidate.id} className="rounded-lg border border-dashed p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{candidate.asset_type}</Badge>
                    <span className="text-sm font-medium">{candidate.title}</span>
                  </div>
                  <p className="text-muted-foreground mt-2 text-sm leading-6">
                    {candidate.content}
                  </p>
                </div>
              ))}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
