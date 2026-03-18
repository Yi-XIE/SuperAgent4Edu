import { getBackendBaseURL } from "../config";

import type { UserMemory } from "./types";

export async function loadMemory(agentName?: string, runId?: string) {
  const search = new URLSearchParams();
  if (agentName) {
    search.set("agent_name", agentName);
  }
  if (runId) {
    search.set("run_id", runId);
  }

  const memory = await fetch(
    `${getBackendBaseURL()}/api/memory${search.size > 0 ? `?${search.toString()}` : ""}`,
  );
  const json = await memory.json();
  return json as UserMemory;
}
