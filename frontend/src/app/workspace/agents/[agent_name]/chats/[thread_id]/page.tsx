"use client";

import { BotIcon, PlusSquare } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef } from "react";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";
import { AgentWelcome } from "@/components/workspace/agent-welcome";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import { ChatBox, useThreadChat } from "@/components/workspace/chats";
import { InputBox } from "@/components/workspace/input-box";
import { EducationMemoryPanel } from "@/components/workspace/messages/education-memory-panel";
import { MessageList } from "@/components/workspace/messages";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { Tooltip } from "@/components/workspace/tooltip";
import { useAgent } from "@/core/agents";
import {
  bootstrapRun,
  decideCheckpoint,
  isEducationAgent,
  updateRun as updateEducationRun,
  useEducationWorkbench,
  type EducationCheckpoint,
} from "@/core/education";
import { useI18n } from "@/core/i18n/hooks";
import { useNotification } from "@/core/notification/hooks";
import { useLocalSettings } from "@/core/settings";
import { useThreadStream } from "@/core/threads/hooks";
import { textOfMessage } from "@/core/threads/utils";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export default function AgentChatPage() {
  const { t } = useI18n();
  const [settings, setSettings] = useLocalSettings();
  const router = useRouter();
  const searchParams = useSearchParams();

  const { agent_name } = useParams<{
    agent_name: string;
  }>();

  const { agent } = useAgent(agent_name);
  const isEducationStudio = isEducationAgent(agent_name);

  const { threadId, isNewThread, setIsNewThread } = useThreadChat();
  const runIdFromQuery = searchParams.get("run_id");
  const {
    data: educationWorkbench,
    isLoading: isEducationWorkbenchLoading,
  } = useEducationWorkbench(isEducationStudio && !runIdFromQuery);
  const runIdFromThread = useMemo(() => {
    if (!isEducationStudio || runIdFromQuery) {
      return null;
    }
    return (
      educationWorkbench.runs.find((run) => run.thread_id === threadId)?.id ?? null
    );
  }, [educationWorkbench.runs, isEducationStudio, runIdFromQuery, threadId]);
  const educationRunId = isEducationStudio
    ? (runIdFromQuery ?? runIdFromThread ?? threadId)
    : undefined;
  const bootstrappedRunRef = useRef<string | null>(null);
  const bootstrapPromiseRef = useRef<Promise<void> | null>(null);
  const effectiveContext = useMemo(
    () =>
      isEducationStudio
        ? {
            ...settings.context,
            mode: settings.context.mode ?? ("ultra" as const),
            reasoning_effort:
              settings.context.reasoning_effort ?? ("high" as const),
          }
        : settings.context,
    [isEducationStudio, settings.context],
  );

  useEffect(() => {
    if (!isEducationStudio) {
      return;
    }
    if (!runIdFromQuery && isEducationWorkbenchLoading) {
      return;
    }
    const canonicalRunId = runIdFromQuery ?? runIdFromThread;
    if (!canonicalRunId) {
      return;
    }
    router.replace(`/workspace/education/runs/${canonicalRunId}`);
  }, [
    isEducationStudio,
    isEducationWorkbenchLoading,
    router,
    runIdFromQuery,
    runIdFromThread,
  ]);

  useEffect(() => {
    if (!isEducationStudio || !educationRunId) {
      return;
    }
    if (bootstrappedRunRef.current === educationRunId) {
      return;
    }
    const promise = bootstrapRun(educationRunId)
      .then(() => {
        bootstrappedRunRef.current = educationRunId;
      })
      .catch(() => {
        // Best-effort bootstrap; chat flow should remain available.
      })
      .finally(() => {
        if (bootstrapPromiseRef.current === promise) {
          bootstrapPromiseRef.current = null;
        }
      });
    bootstrapPromiseRef.current = promise;
  }, [educationRunId, isEducationStudio]);

  const ensureEducationBootstrap = useCallback(async () => {
    if (!isEducationStudio || !educationRunId) {
      return;
    }
    if (bootstrappedRunRef.current === educationRunId) {
      return;
    }
    if (bootstrapPromiseRef.current) {
      await bootstrapPromiseRef.current;
      return;
    }
    const promise = bootstrapRun(educationRunId)
      .then(() => {
        bootstrappedRunRef.current = educationRunId;
      })
      .catch(() => {
        // Best-effort bootstrap; chat flow should remain available.
      })
      .finally(() => {
        if (bootstrapPromiseRef.current === promise) {
          bootstrapPromiseRef.current = null;
        }
      });
    bootstrapPromiseRef.current = promise;
    await promise;
  }, [educationRunId, isEducationStudio]);

  const { showNotification } = useNotification();
  const [thread, sendMessage] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: {
      ...effectiveContext,
      agent_name: agent_name,
      ...(educationRunId ? { run_id: educationRunId } : {}),
    },
    onStart: (startedThreadId) => {
      setIsNewThread(false);
      // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
      const runQuery =
        educationRunId && isEducationStudio
          ? `?run_id=${encodeURIComponent(educationRunId)}`
          : "";
      history.replaceState(
        null,
        "",
        `/workspace/agents/${agent_name}/chats/${startedThreadId}${runQuery}`,
      );
      if (educationRunId) {
        void updateEducationRun(educationRunId, {
          thread_id: startedThreadId,
        }).catch(() => {
          // Best-effort binding; chat flow should not be blocked.
        });
      }
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
                ? textContent.substring(0, 200) + "..."
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
        agent_name,
        ...(educationRunId ? { run_id: educationRunId } : {}),
      });
    },
    [sendMessage, threadId, agent_name, educationRunId, ensureEducationBootstrap],
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
          run_id: educationRunId ?? threadId,
          checkpoint_id: checkpoint.checkpoint_id,
          option: value,
        }).catch(() => {
          // Checkpoint state write is best-effort and should not block chat flow.
        });
      }

      await sendMessage(
        threadId,
        {
          text: value,
          files: [],
        },
        {
          agent_name,
          ...(educationRunId ? { run_id: educationRunId } : {}),
        },
      );
    },
    [agent_name, educationRunId, sendMessage, threadId, ensureEducationBootstrap],
  );

  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  if (isEducationStudio && (runIdFromQuery || runIdFromThread)) {
    return (
      <div className="flex size-full items-center justify-center p-6">
        <div className="rounded-xl border p-6 text-sm">
          正在跳转到当前备课主舞台...
        </div>
      </div>
    );
  }

  return (
    <ThreadContext.Provider value={{ thread }}>
      <ChatBox threadId={threadId}>
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center gap-2 px-4",
              isNewThread
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            {/* Agent badge */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1">
              <BotIcon className="text-primary h-3.5 w-3.5" />
              <span className="text-xs font-medium">
                {agent?.name ?? agent_name}
              </span>
            </div>

            <div className="flex w-full items-center text-sm font-medium">
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>
            <div className="mr-4 flex items-center">
              <Tooltip content={t.agents.newChat}>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    router.push(`/workspace/agents/${agent_name}/chats/new`);
                  }}
                >
                  <PlusSquare /> {t.agents.newChat}
                </Button>
              </Tooltip>
              <ArtifactTrigger />
            </div>
          </header>

          <main className="flex min-h-0 max-w-full grow">
            <div className="relative flex min-h-0 grow flex-col">
              <div className="flex size-full justify-center">
                <MessageList
                  className={cn("size-full", !isNewThread && "pt-10")}
                  onClarificationOptionSelect={
                    isEducationStudio ? handleCheckpointOptionSelect : undefined
                  }
                  threadId={threadId}
                  thread={thread}
                />
              </div>

              <div className="absolute right-0 bottom-0 left-0 z-30 flex justify-center px-4">
                <div
                  className={cn(
                    "relative w-full",
                    isNewThread && "-translate-y-[calc(50vh-96px)]",
                    isNewThread
                      ? "max-w-(--container-width-sm)"
                      : "max-w-(--container-width-md)",
                  )}
                >
                  <div className="absolute -top-4 right-0 left-0 z-0">
                    <div className="absolute right-0 bottom-0 left-0">
                      <TodoList
                        className="bg-background/5"
                        todos={thread.values.todos ?? []}
                        hidden={
                          !thread.values.todos ||
                          thread.values.todos.length === 0
                        }
                      />
                    </div>
                  </div>

                  <InputBox
                    className={cn("bg-background/5 w-full -translate-y-4")}
                    isNewThread={isNewThread}
                    threadId={threadId}
                    autoFocus={isNewThread}
                    status={thread.isLoading ? "streaming" : "ready"}
                    context={effectiveContext}
                    extraHeader={
                      isNewThread && (
                        <AgentWelcome agent={agent} agentName={agent_name} />
                      )
                    }
                    disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                    onContextChange={(context) =>
                      setSettings("context", context)
                    }
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                  />
                  {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
                    <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                      {t.common.notAvailableInDemoMode}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {isEducationStudio && (
              <EducationMemoryPanel
                agentName={agent_name}
                runId={educationRunId ?? threadId}
              />
            )}
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
