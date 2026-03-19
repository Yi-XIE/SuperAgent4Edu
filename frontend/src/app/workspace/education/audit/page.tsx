"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EducationSectionShell } from "@/components/workspace/education/education-section-shell";
import { useEducationWorkbench } from "@/core/education";

function timeLabel(value?: string | null) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

export default function EducationAuditPage() {
  const { data } = useEducationWorkbench();

  return (
    <EducationSectionShell
      description="审计治理从教师主舞台拆出，保留后台视图用于排查和治理。"
      title="审计日志"
    >
      <Card>
        <CardHeader>
          <CardTitle className="text-base">最近 60 条审计日志</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.auditLogs.length === 0 && (
            <p className="text-muted-foreground text-sm">暂无审计记录</p>
          )}
          {data.auditLogs.map((log) => (
            <div key={log.id} className="rounded-lg border p-3">
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
    </EducationSectionShell>
  );
}
