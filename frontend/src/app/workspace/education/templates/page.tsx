"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEducationWorkbench } from "@/core/education";

export default function EducationTemplatesPage() {
  const { data, isLoading, error } = useEducationWorkbench();
  const templates = data.templates;

  return (
    <div className="flex size-full flex-col">
      <div className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold">智能体和工作流</h1>
        <p className="text-muted-foreground mt-0.5 text-sm">
          查看工作流模板与发布状态。
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
            正在加载模板...
          </div>
        ) : templates.length === 0 ? (
          <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-sm">
            暂无模板。
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {templates.map((template) => (
              <Card key={template.id} className="flex h-full flex-col">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">{template.name}</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-3">
                  <p className="text-muted-foreground line-clamp-4 text-sm">
                    {template.description ?? "无描述"}
                  </p>
                  <div className="mt-auto flex flex-wrap gap-2">
                    <Badge>{template.type}</Badge>
                    <Badge variant="outline">{template.status}</Badge>
                    <Badge variant="secondary">v{template.version}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border p-4 text-sm">
            <p className="text-destructive">
              读取模板失败：{error instanceof Error ? error.message : "未知错误"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
