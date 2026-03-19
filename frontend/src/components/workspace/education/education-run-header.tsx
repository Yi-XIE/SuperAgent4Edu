"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { type EducationRunState } from "@/core/education";

function timeLabel(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export function EducationRunHeader({
  run,
}: {
  run: EducationRunState;
}) {
  return (
    <Card className="w-full">
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="text-lg font-semibold">{run.title}</p>
            <p className="text-muted-foreground text-sm">
              run_id: {run.id} | 更新时间：{timeLabel(run.updated_at)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">{run.status}</Badge>
            <Badge variant="secondary">{run.current_stage}</Badge>
            <Badge variant="secondary">{run.generation_mode}</Badge>
            <Badge variant={run.critic_enabled ? "default" : "outline"}>
              {run.critic_enabled ? "Critic 开启" : "Critic 关闭"}
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="outline">Blueprint: {run.blueprint_status}</Badge>
          <Badge variant="outline">Package: {run.package_status}</Badge>
          <Badge variant="outline">
            Extraction: {run.asset_extraction_status}
          </Badge>
          {run.critic_activation_reason && (
            <Badge variant="secondary">
              Critic 原因：{run.critic_activation_reason}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
