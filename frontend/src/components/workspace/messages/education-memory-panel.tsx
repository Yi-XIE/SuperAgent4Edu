"use client";

import { BookOpenCheckIcon, BrainCircuitIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMemory } from "@/core/memory/hooks";
import { cn } from "@/lib/utils";

const CATEGORY_LABELS: Record<string, string> = {
  teacher_preference: "教师偏好",
  course_continuity: "课程连续性",
  learning_kit_preference: "学具偏好",
  team_template: "团队模板",
};

export function EducationMemoryPanel({
  className,
  agentName,
  runId,
}: {
  className?: string;
  agentName: string;
  runId: string;
}) {
  const { memory, isLoading, error } = useMemory(agentName, runId);

  if (isLoading || error || !memory) {
    return null;
  }

  const groupedFacts = Object.keys(CATEGORY_LABELS).map((category) => {
    const facts = memory.facts
      .filter((fact) => fact.category === category && typeof fact.content === "string")
      .slice(0, 2);
    return {
      category,
      label: CATEGORY_LABELS[category] ?? category,
      facts,
    };
  });

  const educationSignals = memory.education_signals ?? [];
  const usedSignals = memory.used_signals ?? [];
  const hasContent =
    groupedFacts.some((item) => item.facts.length > 0) ||
    educationSignals.length > 0 ||
    usedSignals.length > 0;

  if (!hasContent) {
    return null;
  }

  return (
    <aside className={cn("bg-background/40 hidden w-80 shrink-0 border-l xl:block", className)}>
      <div className="h-full overflow-y-auto p-4 pt-16">
        <Card className="mb-4 gap-3">
          <CardHeader className="gap-2">
            <div className="flex items-center gap-2">
              <BookOpenCheckIcon className="text-primary h-4 w-4" />
              <CardTitle className="text-sm">教师记忆区</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {groupedFacts.map((item) => (
              <div key={item.category} className="space-y-1">
                <Badge variant="secondary">{item.label}</Badge>
                {item.facts.length === 0 ? (
                  <p className="text-muted-foreground text-xs">暂无稳定记忆</p>
                ) : (
                  item.facts.map((fact) => (
                    <p
                      key={fact.id}
                      className="text-muted-foreground text-xs leading-5"
                    >
                      {fact.content}
                    </p>
                  ))
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="gap-3">
          <CardHeader className="gap-2">
            <div className="flex items-center gap-2">
              <BrainCircuitIcon className="text-primary h-4 w-4" />
              <CardTitle className="text-sm">本次使用信号</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {usedSignals.length === 0 ? (
              <p className="text-muted-foreground text-xs">本轮暂无可展示信号</p>
            ) : (
              usedSignals.slice(0, 8).map((signal, index) => (
                <div
                  key={`${signal.category}-${signal.content}-${index}`}
                  className="space-y-1 rounded border p-2"
                >
                  <p className="text-xs font-medium">
                    {CATEGORY_LABELS[signal.category] ?? signal.category}
                  </p>
                  <p className="text-muted-foreground text-xs leading-5">
                    {signal.content}
                  </p>
                  <p className="text-muted-foreground text-[11px]">
                    来源：{signal.source}
                  </p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {educationSignals.length > 0 && (
          <Card className="mt-4 gap-3">
            <CardHeader className="gap-2">
              <CardTitle className="text-sm">长期信号候选</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {educationSignals.slice(0, 6).map((signal, index) => (
                <div
                  key={`durable-${signal.category}-${index}`}
                  className="space-y-1 rounded border p-2"
                >
                  <p className="text-xs font-medium">
                    {CATEGORY_LABELS[signal.category] ?? signal.category}
                  </p>
                  <p className="text-muted-foreground text-xs leading-5">
                    {signal.content}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </aside>
  );
}
