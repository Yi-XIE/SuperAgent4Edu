"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { uuid } from "@/core/utils/uuid";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isUUID(value: string | undefined) {
  return Boolean(value && UUID_RE.test(value));
}

export function useThreadChat() {
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const searchParams = useSearchParams();
  const isPathNew = threadIdFromPath === "new";
  const isPathInvalid = !isPathNew && !isUUID(threadIdFromPath);
  const shouldCreateNewThread = isPathNew || isPathInvalid;
  const prevPathRef = useRef<string | undefined>(threadIdFromPath);

  const [threadId, setThreadId] = useState(() => {
    return shouldCreateNewThread ? uuid() : threadIdFromPath;
  });

  const [isNewThread, setIsNewThread] = useState(
    () => shouldCreateNewThread,
  );

  useEffect(() => {
    if (prevPathRef.current === threadIdFromPath) {
      return;
    }
    prevPathRef.current = threadIdFromPath;

    if (shouldCreateNewThread) {
      const nextThreadId = uuid();
      setIsNewThread((prev) => (prev ? prev : true));
      setThreadId((prev) => (prev === nextThreadId ? prev : nextThreadId));
      return;
    }

    setIsNewThread((prev) => (prev ? false : prev));
    setThreadId((prev) => (prev === threadIdFromPath ? prev : threadIdFromPath));
  }, [shouldCreateNewThread, threadIdFromPath]);

  const isMock = searchParams.get("mock") === "true";
  return { threadId, isNewThread, setIsNewThread, isMock };
}
