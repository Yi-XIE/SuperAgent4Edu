"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EducationSectionShell } from "@/components/workspace/education/education-section-shell";
import { useEducationWorkbench } from "@/core/education";

export default function EducationResourcesPage() {
  const { data } = useEducationWorkbench();

  return (
    <EducationSectionShell
      description="资源库和教师素材台保留独立入口，避免在单次备课主舞台里打断主流程。"
      title="资源库"
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-base">资源列表</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.resources.length === 0 && (
            <p className="text-muted-foreground text-sm">暂无资源</p>
          )}
          {data.resources.map((resource) => (
            <div key={resource.id} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{resource.title}</span>
                <Badge variant="outline">{resource.source_type}</Badge>
                <Badge variant="secondary">
                  {resource.whitelisted ? "白名单" : "未白名单"}
                </Badge>
              </div>
              <p className="text-muted-foreground mt-1 text-xs">{resource.url}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">教师素材台预览</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.assets.slice(0, 8).map((asset) => (
            <div key={asset.id} className="rounded-lg border p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge>{asset.asset_type}</Badge>
                <span className="font-medium">{asset.title}</span>
              </div>
              <p className="text-muted-foreground mt-1 text-xs">{asset.content}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </EducationSectionShell>
  );
}
