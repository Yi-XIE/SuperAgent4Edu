"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type EducationRunState } from "@/core/education";
import { cn } from "@/lib/utils";

type RailStatus = "pending" | "running" | "completed";

function resolveRailItems(run: EducationRunState) {
  const cp1Done = run.checkpoint_history.some(
    (item) => item.checkpoint_id === "cp1-task-confirmation",
  );
  const cp3Done = run.checkpoint_history.some(
    (item) => item.checkpoint_id === "cp3-draft-review",
  );

  const taskBriefStatus: RailStatus = cp1Done
    ? "completed"
    : run.status === "awaiting_checkpoint" || run.current_stage === "Stage 0"
      ? "running"
      : "pending";

  const blueprintStatus: RailStatus =
    run.blueprint_status === "completed"
      ? "completed"
      : run.blueprint_status === "running"
        ? "running"
        : "pending";

  const packageStatus: RailStatus =
    run.package_status === "completed"
      ? "completed"
      : run.package_status === "running"
        ? "running"
        : "pending";

  const reviewStatus: RailStatus =
    cp3Done || run.status === "accepted" || run.status === "closed"
      ? "completed"
      : run.reviewer_summary || run.critic_summary
        ? "running"
        : "pending";

  const extractionStatus: RailStatus =
    run.asset_extraction_status === "confirmed" ||
    run.asset_extraction_status === "skipped"
      ? "completed"
      : run.asset_extraction_status === "ready_for_confirmation"
        ? "running"
        : "pending";

  return [
    { label: "任务简报", status: taskBriefStatus },
    { label: "课程蓝图", status: blueprintStatus },
    { label: "完整课包", status: packageStatus },
    { label: "质量评审", status: reviewStatus },
    { label: "素材提取", status: extractionStatus },
  ];
}

function badgeVariant(status: RailStatus): "outline" | "secondary" | "default" {
  if (status === "completed") {
    return "default";
  }
  if (status === "running") {
    return "secondary";
  }
  return "outline";
}

export function EducationStageRail({
  run,
}: {
  run: EducationRunState;
}) {
  const items = resolveRailItems(run);

  return (
    <Card className="w-full gap-4">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">当前阶段</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-5">
        {items.map((item, index) => (
          <div
            key={item.label}
            className={cn(
              "rounded-lg border p-3",
              item.status === "running" && "border-primary/40 bg-primary/5",
            )}
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-medium">0{index + 1}</span>
              <Badge variant={badgeVariant(item.status)}>{item.status}</Badge>
            </div>
            <p className="text-sm font-medium">{item.label}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
