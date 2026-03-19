"use client";

import type { Message } from "@langchain/langgraph-sdk";
import { useQuery } from "@tanstack/react-query";
import { PlusSquare } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import { ChatBox } from "@/components/workspace/chats";
import { EducationGenerationModeCard } from "@/components/workspace/education/education-generation-mode-card";
import { EducationResultPanel } from "@/components/workspace/education/education-result-panel";
import { EducationRunHeader } from "@/components/workspace/education/education-run-header";
import { EducationRunSidebar } from "@/components/workspace/education/education-run-sidebar";
import { EducationStageRail } from "@/components/workspace/education/education-stage-rail";
import { EducationStarterPanel } from "@/components/workspace/education/education-starter-panel";
import { EducationTaskBriefCard } from "@/components/workspace/education/education-task-brief-card";
import { InputBox } from "@/components/workspace/input-box";
import { MessageList } from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { EducationMemoryPanel } from "@/components/workspace/messages/education-memory-panel";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { Tooltip } from "@/components/workspace/tooltip";
import {
  bootstrapRun,
  buildEducationStarterPrompt,
  decideCheckpoint,
  EDUCATION_AGENT_NAME,
  getRunResult,
  parseEducationGenerationModeCard,
  parseEducationTaskBriefCard,
  updateRun as updateEducationRun,
  useEducationWorkbench,
  type EducationCheckpoint,
  type EducationStarterMode,
} from "@/core/education";
import { extractContentFromMessage, hasContent } from "@/core/messages/utils";
import { useNotification } from "@/core/notification/hooks";
import { useLocalSettings } from "@/core/settings";
import { useThreadStream } from "@/core/threads/hooks";
import { textOfMessage } from "@/core/threads/utils";
import { uuid } from "@/core/utils/uuid";
import { env } from "@/env";
import { cn } from "@/lib/utils";

function findLatestEducationCards(messages: Message[]) {
  let taskBriefCard: ReturnType<typeof parseEducationTaskBriefCard> = null;
  let generationModeCard: ReturnType<typeof parseEducationGenerationModeCard> = null;

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (!message || message.type !== "ai") {
      continue;
    }
    if (hasContent(message)) {
      const content = extractContentFromMessage(message);
      taskBriefCard ??= parseEducationTaskBriefCard(content);
      generationModeCard ??= parseEducationGenerationModeCard(content);
      if (taskBriefCard && generationModeCard) {
        break;
      }
    }
  }

  return {
    taskBriefCard,
    generationModeCard,
  };
}

export function EducationRunWorkbenchShell({
  runId,
}: {
  runId: string;
}) {
  const router = useRouter();
  const [settings, setSettings] = useLocalSettings();
  const { data, isLoading, error } = useEducationWorkbench();
  const runFromWorkbench = useMemo(
    () => data.runs.find((item) => item.id === runId) ?? null,
    [data.runs, runId],
  );
  const runResultFromWorkbench = runFromWorkbench
    ? data.runResults[runFromWorkbench.id] ?? null
    : null;
  const fallbackRunResultQuery = useQuery({
    queryKey: ["education", "run-result-fallback", runId],
    queryFn: () => getRunResult(runId),
    enabled: !isLoading && !runFromWorkbench,
  });
  const run = runFromWorkbench ?? fallbackRunResultQuery.data?.run ?? null;
  const runResult = runResultFromWorkbench ?? fallbackRunResultQuery.data ?? null;

  const [threadId, setThreadId] = useState<string>(() => run?.thread_id ?? uuid());
  const [isNewThread, setIsNewThread] = useState<boolean>(() => !run?.thread_id);
  const [starterMode, setStarterMode] = useState<EducationStarterMode | null>(null);

  const bootstrappedRunRef = useRef<string | null>(null);
  const bootstrapPromiseRef = useRef<Promise<void> | null>(null);

  useEffect(() => {
    const nextThreadId = run?.thread_id;
    if (!nextThreadId) {
      return;
    }
    setThreadId((prev) => (prev === nextThreadId ? prev : nextThreadId));
    setIsNewThread(false);
  }, [run?.thread_id]);

  const effectiveContext = useMemo(
    () => ({
      ...settings.context,
      mode: settings.context.mode ?? ("ultra" as const),
      reasoning_effort: settings.context.reasoning_effort ?? ("high" as const),
    }),
    [settings.context],
  );

  useEffect(() => {
    if (!runId) {
      return;
    }
    if (bootstrappedRunRef.current === runId) {
      return;
    }
    const promise = bootstrapRun(runId)
      .then(() => {
        bootstrappedRunRef.current = runId;
      })
      .catch(() => {
        // Best-effort bootstrap; the run page should remain available.
      })
      .finally(() => {
        if (bootstrapPromiseRef.current === promise) {
          bootstrapPromiseRef.current = null;
        }
      });
    bootstrapPromiseRef.current = promise;
  }, [runId]);

  const ensureEducationBootstrap = useCallback(async () => {
    if (bootstrappedRunRef.current === runId) {
      return;
    }
    if (bootstrapPromiseRef.current) {
      await bootstrapPromiseRef.current;
      return;
    }
    const promise = bootstrapRun(runId)
      .then(() => {
        bootstrappedRunRef.current = runId;
      })
      .catch(() => {
        // Best-effort bootstrap; the run page should remain available.
      })
      .finally(() => {
        if (bootstrapPromiseRef.current === promise) {
          bootstrapPromiseRef.current = null;
        }
      });
    bootstrapPromiseRef.current = promise;
    await promise;
  }, [runId]);

  const { showNotification } = useNotification();
  const [thread, sendMessage] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: {
      ...effectiveContext,
      agent_name: EDUCATION_AGENT_NAME,
      run_id: runId,
    },
    onStart: (startedThreadId) => {
      setIsNewThread(false);
      setThreadId(startedThreadId);
      void updateEducationRun(runId, {
        thread_id: startedThreadId,
      }).catch(() => {
        // Best-effort binding; main chat flow should not be blocked.
      });
      history.replaceState(null, "", `/workspace/education/runs/${runId}`);
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages[state.messages.length - 1];
        if (lastMessage) {
          const textContent = textOfMessage(lastMessage);
          if (textContent) {
            body =
              textContent.length > 200
                ? `${textContent.substring(0, 200)}...`
                : textContent;
          }
        }
        showNotification(state.title, { body });
      }
    },
  });

  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      await ensureEducationBootstrap();
      await sendMessage(threadId, message, {
        agent_name: EDUCATION_AGENT_NAME,
        run_id: runId,
      });
    },
    [ensureEducationBootstrap, runId, sendMessage, threadId],
  );

  const handleCheckpointOptionSelect = useCallback(
    async (value: string, checkpoint: EducationCheckpoint) => {
      await ensureEducationBootstrap();
      if (
        checkpoint.checkpoint_id === "cp1-task-confirmation" ||
        checkpoint.checkpoint_id === "cp2-goal-lock" ||
        checkpoint.checkpoint_id === "cp3-draft-review" ||
        checkpoint.checkpoint_id === "cp4-asset-extraction-confirm"
      ) {
        void decideCheckpoint({
          run_id: runId,
          checkpoint_id: checkpoint.checkpoint_id,
          option: value,
        }).catch(() => {
          // Best-effort state write; should not block the chat flow.
        });
      }

      await sendMessage(
        threadId,
        {
          text: value,
          files: [],
        },
        {
          agent_name: EDUCATION_AGENT_NAME,
          run_id: runId,
        },
      );
    },
    [ensureEducationBootstrap, runId, sendMessage, threadId],
  );

  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  const handleStarterMode = useCallback(
    async (mode: EducationStarterMode) => {
      setStarterMode(mode);
      await ensureEducationBootstrap();
      await sendMessage(
        threadId,
        {
          text: buildEducationStarterPrompt(mode),
          files: [],
        },
        {
          agent_name: EDUCATION_AGENT_NAME,
          run_id: runId,
        },
      );
    },
    [ensureEducationBootstrap, runId, sendMessage, threadId],
  );

  const handleCardApply = useCallback(
    async (content: string) => {
      await ensureEducationBootstrap();
      await sendMessage(
        threadId,
        {
          text: content,
          files: [],
        },
        {
          agent_name: EDUCATION_AGENT_NAME,
          run_id: runId,
        },
      );
    },
    [ensureEducationBootstrap, runId, sendMessage, threadId],
  );

  const { taskBriefCard: parsedTaskBriefCard, generationModeCard: parsedGenerationModeCard } = useMemo(
    () => findLatestEducationCards(thread.messages),
    [thread.messages],
  );

  if (isLoading || fallbackRunResultQuery.isLoading) {
    return (
      <div className="flex size-full items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-xl border p-6 text-sm">
          {isLoading && <p>正在加载当前备课任务...</p>}
          {!isLoading && fallbackRunResultQuery.isLoading && (
            <p>正在加载课包详情...</p>
          )}
          {error && (
            <p className="text-destructive mt-2">
              {error instanceof Error ? error.message : "读取任务失败"}
            </p>
          )}
          {fallbackRunResultQuery.error && (
            <p className="text-destructive mt-2">
              {fallbackRunResultQuery.error instanceof Error
                ? fallbackRunResultQuery.error.message
                : "读取课包详情失败"}
            </p>
          )}
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex size-full items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-xl border p-6 text-sm">
          <p>没有找到对应的课包（run_id: {runId}）。</p>
          {error && (
            <p className="text-destructive mt-2">
              {error instanceof Error ? error.message : "读取任务失败"}
            </p>
          )}
          {fallbackRunResultQuery.error && (
            <p className="text-destructive mt-2">
              {fallbackRunResultQuery.error instanceof Error
                ? fallbackRunResultQuery.error.message
                : "读取课包详情失败"}
            </p>
          )}
          <div className="mt-3">
            <Button
              variant="outline"
              onClick={() => {
                router.push("/workspace/education");
              }}
            >
              返回知识花园
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ThreadContext.Provider value={{ thread }}>
      <ChatBox threadId={threadId}>
        <div className="flex size-full min-h-0 gap-4 p-4">
          <EducationRunSidebar
            assets={data.assets}
            currentRunId={run.id}
            resources={data.resources}
            runs={data.runs}
          />

          <main className="flex min-h-0 min-w-0 flex-1 gap-4">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
              <EducationRunHeader run={run} />
              <EducationStageRail run={run} />

              {isNewThread && thread.messages.length === 0 && (
                <EducationStarterPanel
                  disabled={thread.isLoading}
                  onStart={(mode) => {
                    void handleStarterMode(mode);
                  }}
                />
              )}

              {parsedTaskBriefCard && (
                <EducationTaskBriefCard
                  card={parsedTaskBriefCard}
                  disabled={thread.isLoading}
                  editable
                  onApply={(content) => {
                    void handleCardApply(content);
                  }}
                />
              )}

              {!parsedGenerationModeCard && starterMode && thread.messages.length === 1 && (
                <EducationGenerationModeCard
                  card={{
                    title: "生成策略确认卡",
                    summary:
                      starterMode === "quick_generate"
                        ? "你通过“快速生成课包”进入，本轮默认建议先从零生成，再根据课堂限制逐步补充。"
                        : "你通过“带着已有想法生成”进入，本轮默认建议优先吸收已有素材和想法，再生成课程蓝图。",
                    recommended_mode:
                      starterMode === "quick_generate"
                        ? "from_scratch"
                        : "material_first",
                    options: [
                      {
                        mode: "from_scratch",
                        description: "从主题和基础约束出发，适合从零开始梳理。",
                      },
                      {
                        mode: "material_first",
                        description: "优先吸收现有目标、活动点子和已有素材。",
                      },
                      {
                        mode: "mixed",
                        description: "同时参考已有素材和外部研究，适合已有想法但还不完整的任务。",
                      },
                    ],
                    rawContent: "",
                  }}
                  disabled={thread.isLoading}
                  editable
                  onApply={(content) => {
                    void handleCardApply(content);
                  }}
                />
              )}

              {parsedGenerationModeCard && (
                <EducationGenerationModeCard
                  card={parsedGenerationModeCard}
                  disabled={thread.isLoading}
                  editable
                  onApply={(content) => {
                    void handleCardApply(content);
                  }}
                />
              )}

              <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden rounded-2xl border">
                <header className="bg-background/80 flex h-12 shrink-0 items-center gap-2 border-b px-4 backdrop-blur">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <span className="truncate text-sm font-medium">
                      <ThreadTitle thread={thread} threadId={threadId} />
                    </span>
                  </div>
                  <Tooltip content="打开新备课">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        router.push("/workspace/education");
                      }}
                    >
                      <PlusSquare className="h-4 w-4" />
                      新建备课
                    </Button>
                  </Tooltip>
                  <ArtifactTrigger />
                </header>

                <div className="flex h-[calc(100%-3rem)] min-h-0 flex-col">
                  <div className="flex min-h-0 flex-1 justify-center overflow-hidden">
                    <MessageList
                      className="size-full"
                      disableEducationInfoCards
                      forceEducationStudio
                      onClarificationOptionSelect={handleCheckpointOptionSelect}
                      paddingBottom={196}
                      thread={thread}
                      threadId={threadId}
                    />
                  </div>

                  <div className="absolute right-0 bottom-0 left-0 z-20 flex justify-center px-4 pb-4">
                    <div className="relative w-full max-w-(--container-width-md)">
                      <div className="absolute -top-4 right-0 left-0 z-0">
                        <div className="absolute right-0 bottom-0 left-0">
                          <TodoList
                            className="bg-background/5"
                            hidden={
                              !thread.values.todos ||
                              thread.values.todos.length === 0
                            }
                            todos={thread.values.todos ?? []}
                          />
                        </div>
                      </div>
                      <InputBox
                        className={cn("bg-background/5 w-full -translate-y-4")}
                        context={effectiveContext}
                        disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                        isNewThread={isNewThread}
                        onContextChange={(context) =>
                          setSettings("context", context)
                        }
                        onStop={handleStop}
                        onSubmit={handleSubmit}
                        status={thread.isLoading ? "streaming" : "ready"}
                        threadId={threadId}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <aside className="hidden w-[360px] shrink-0 xl:flex xl:flex-col xl:gap-4">
              <EducationResultPanel result={runResult} />
              <EducationMemoryPanel agentName={EDUCATION_AGENT_NAME} runId={runId} />
            </aside>
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
