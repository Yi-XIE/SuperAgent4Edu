"use client";

import { GraduationCapIcon, LightbulbIcon, SparklesIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type EducationStarterMode } from "@/core/education";

export function EducationStarterPanel({
  disabled = false,
  onStart,
}: {
  disabled?: boolean;
  onStart: (mode: EducationStarterMode) => void;
}) {
  return (
    <Card className="w-full gap-4 border-dashed">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-full">
            <GraduationCapIcon className="text-primary h-5 w-5" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-base">开始一节新的备课任务</CardTitle>
            <p className="text-muted-foreground text-sm">
              通过对话进入。先让我整理任务简报，再确认生成策略，然后进入课程蓝图与完整课包。
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        <button
          className="hover:border-primary/50 hover:bg-muted/40 rounded-xl border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          onClick={() => onStart("quick_generate")}
          type="button"
        >
          <div className="mb-3 flex items-center gap-2 text-sm font-medium">
            <SparklesIcon className="h-4 w-4" />
            快速生成课包
          </div>
          <p className="text-muted-foreground text-sm leading-6">
            适合从零开始。先给出主题、年级、课时，再在对话中逐步补齐任务约束。
          </p>
        </button>
        <button
          className="hover:border-primary/50 hover:bg-muted/40 rounded-xl border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          disabled={disabled}
          onClick={() => onStart("idea_first")}
          type="button"
        >
          <div className="mb-3 flex items-center gap-2 text-sm font-medium">
            <LightbulbIcon className="h-4 w-4" />
            带着已有想法生成
          </div>
          <p className="text-muted-foreground text-sm leading-6">
            适合已经有目标、活动点子或学具限制。系统会先吸收已有内容，再整理任务简报和生成策略。
          </p>
        </button>
        <div className="md:col-span-2">
          <Button
            className="w-full justify-start"
            disabled={disabled}
            variant="outline"
            onClick={() => onStart("quick_generate")}
          >
            直接开始对话
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
