"use client";

import { BotIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { type Agent } from "@/core/agents";
import {
  getEducationPromptTemplate,
  isEducationAgent,
} from "@/core/education";
import { cn } from "@/lib/utils";

export function AgentWelcome({
  className,
  agent,
  agentName,
}: {
  className?: string;
  agent: Agent | null | undefined;
  agentName: string;
}) {
  const displayName = agent?.name ?? agentName;
  const description = agent?.description;
  const isEducationStudio = isEducationAgent(agentName);

  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-col items-center justify-center gap-2 px-8 py-4 text-center",
        className,
      )}
    >
      <div className="bg-primary/10 flex h-12 w-12 items-center justify-center rounded-full">
        <BotIcon className="text-primary h-6 w-6" />
      </div>
      <div className="text-2xl font-bold">{displayName}</div>
      {description && (
        <p className="text-muted-foreground max-w-sm text-sm">{description}</p>
      )}
      {isEducationStudio && (
        <div className="bg-background/70 mt-2 flex w-full max-w-2xl flex-col gap-3 rounded-2xl border p-4 text-left">
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">小学</Badge>
            <Badge variant="secondary">AI 教育</Badge>
            <Badge variant="secondary">科学教育</Badge>
            <Badge variant="secondary">UbD</Badge>
            <Badge variant="secondary">PBL</Badge>
            <Badge variant="secondary">课程为主，学具为辅</Badge>
          </div>
          <p className="text-muted-foreground text-sm leading-6">
            适合输入一个完整的教师任务简报。这个 agent 会自动按多代理工作流运行，并默认使用
            Ultra 编排模式。
          </p>
          <pre className="bg-muted/60 overflow-x-auto rounded-xl p-3 text-xs leading-6 whitespace-pre-wrap">
            {getEducationPromptTemplate()}
          </pre>
        </div>
      )}
    </div>
  );
}
