import { useQuery } from "@tanstack/react-query";

import { loadMemory } from "./api";

export function useMemory(agentName?: string, runId?: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["memory", agentName ?? "global", runId ?? "no-run"],
    queryFn: () => loadMemory(agentName, runId),
  });
  return { memory: data ?? null, isLoading, error };
}
