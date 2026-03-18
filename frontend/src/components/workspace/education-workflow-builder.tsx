"use client";

import {
  ArrowDownIcon,
  ArrowUpIcon,
  GripVerticalIcon,
  RotateCcwIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

type WorkflowNodeId =
  | "blueprint"
  | "package"
  | "reviewer"
  | "critic"
  | "cp3"
  | "cp4"
  | "present";

type StageNodeId = "blueprint" | "package" | "reviewer" | "critic";

type StageEnabledMap = Record<StageNodeId, boolean>;

const DEFAULT_NODE_ORDER: WorkflowNodeId[] = [
  "blueprint",
  "package",
  "reviewer",
  "critic",
  "cp3",
  "cp4",
  "present",
];

const STAGE_NODE_IDS: StageNodeId[] = [
  "blueprint",
  "package",
  "reviewer",
  "critic",
];

const NODE_META: Record<
  WorkflowNodeId,
  {
    label: string;
    kind: "stage" | "checkpoint" | "delivery";
    aliases: string[];
    contentToken: string;
  }
> = {
  blueprint: {
    label: "Blueprint",
    kind: "stage",
    aliases: ["blueprint", "stage1", "ubd stage 1", "目标蓝图"],
    contentToken: "Blueprint",
  },
  package: {
    label: "Package",
    kind: "stage",
    aliases: [
      "package",
      "stage2",
      "stage3",
      "presentation",
      "learning-kit",
      "learning kit",
      "完整课包",
    ],
    contentToken: "Package",
  },
  reviewer: {
    label: "Reviewer",
    kind: "stage",
    aliases: ["reviewer", "质量评审"],
    contentToken: "Reviewer",
  },
  critic: {
    label: "Critic",
    kind: "stage",
    aliases: ["critic", "挑战性复核", "挑战复核"],
    contentToken: "Critic",
  },
  cp3: {
    label: "Checkpoint 3",
    kind: "checkpoint",
    aliases: ["checkpoint3", "checkpoint 3", "cp3", "草案评审点"],
    contentToken: "Checkpoint3",
  },
  cp4: {
    label: "Checkpoint 4",
    kind: "checkpoint",
    aliases: [
      "checkpoint4",
      "checkpoint 4",
      "cp4",
      "asset extraction",
      "素材提取确认",
    ],
    contentToken: "Checkpoint4",
  },
  present: {
    label: "Present Files",
    kind: "delivery",
    aliases: ["presentfiles", "present files", "present_files", "交付"],
    contentToken: "PresentFiles",
  },
};

function normalizeText(value: string) {
  return value.trim().toLowerCase().replace(/[_\s-]+/g, " ");
}

function parseNodeId(value: string): WorkflowNodeId | null {
  const normalized = normalizeText(value);
  for (const [id, meta] of Object.entries(NODE_META) as Array<
    [WorkflowNodeId, (typeof NODE_META)[WorkflowNodeId]]
  >) {
    for (const alias of meta.aliases) {
      if (normalized.includes(normalizeText(alias))) {
        return id;
      }
    }
  }
  return null;
}

function dedupeOrder(order: WorkflowNodeId[]) {
  const seen = new Set<WorkflowNodeId>();
  const result: WorkflowNodeId[] = [];
  for (const id of order) {
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    result.push(id);
  }
  for (const id of DEFAULT_NODE_ORDER) {
    if (!seen.has(id)) {
      result.push(id);
    }
  }
  return result;
}

function parseGuardMax(content: Record<string, unknown>): number {
  const guard = content.guard;
  if (
    guard &&
    typeof guard === "object" &&
    typeof (guard as { max_local_rework?: unknown }).max_local_rework ===
      "number"
  ) {
    const value = (guard as { max_local_rework: number }).max_local_rework;
    return Number.isFinite(value) && value >= 0 ? value : 1;
  }
  const rerunGuard = content.rerun_guard;
  if (typeof rerunGuard === "string") {
    const marker = "max_local_rework=";
    if (rerunGuard.includes(marker)) {
      const parsed = Number(rerunGuard.split(marker, 2)[1]);
      if (Number.isFinite(parsed) && parsed >= 0) {
        return parsed;
      }
    }
  }
  return 1;
}

function parseWorkflowContent(rawJson: string) {
  let content: Record<string, unknown>;
  try {
    const parsed = JSON.parse(rawJson) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {
        content: {} as Record<string, unknown>,
        parseError: "当前模板不是对象 JSON，拖拽编辑器使用默认配置。",
      };
    }
    content = parsed as Record<string, unknown>;
  } catch {
    return {
      content: {} as Record<string, unknown>,
      parseError: "JSON 格式不正确，拖拽编辑器将使用默认配置。",
    };
  }

  return {
    content,
    parseError: null,
  };
}

function deriveNodeOrder(content: Record<string, unknown>) {
  const rawNodes = Array.isArray(content.nodes) ? content.nodes : [];
  const mapped: WorkflowNodeId[] = [];
  for (const item of rawNodes) {
    if (typeof item !== "string") {
      continue;
    }
    const nodeId = parseNodeId(item);
    if (nodeId !== null) {
      mapped.push(nodeId);
    }
  }
  return dedupeOrder(mapped.length > 0 ? mapped : DEFAULT_NODE_ORDER);
}

function deriveEnabledStages(
  content: Record<string, unknown>,
  nodeOrder: WorkflowNodeId[],
): StageEnabledMap {
  const defaults: StageEnabledMap = {
    blueprint: true,
    package: true,
    reviewer: true,
    critic: true,
  };

  const rawEnabled = Array.isArray(content.enabled_stages)
    ? content.enabled_stages
    : Array.isArray(content.nodes)
      ? content.nodes
      : [];
  const parsed = new Set<StageNodeId>();

  for (const item of rawEnabled) {
    if (typeof item !== "string") {
      continue;
    }
    const nodeId = parseNodeId(item);
    if (
      nodeId === "blueprint" ||
      nodeId === "package" ||
      nodeId === "reviewer" ||
      nodeId === "critic"
    ) {
      parsed.add(nodeId);
    }
  }

  if (parsed.size === 0) {
    for (const id of nodeOrder) {
      if (
        id === "blueprint" ||
        id === "package" ||
        id === "reviewer" ||
        id === "critic"
      ) {
        parsed.add(id);
      }
    }
  }

  const next = { ...defaults };
  for (const id of STAGE_NODE_IDS) {
    next[id] = parsed.has(id);
  }
  return next;
}

function deriveCp4Enabled(content: Record<string, unknown>) {
  const checkpoints = content.checkpoints;
  if (checkpoints && typeof checkpoints === "object") {
    const value = (checkpoints as Record<string, unknown>)[
      "cp4-asset-extraction-confirm"
    ];
    if (typeof value === "boolean") {
      return value;
    }
    const short = (checkpoints as Record<string, unknown>).cp4;
    if (typeof short === "boolean") {
      return short;
    }
  }
  return true;
}

function reorderNodes(
  nodes: WorkflowNodeId[],
  fromId: WorkflowNodeId,
  toId: WorkflowNodeId,
) {
  if (fromId === toId) {
    return nodes;
  }
  const fromIndex = nodes.indexOf(fromId);
  const toIndex = nodes.indexOf(toId);
  if (fromIndex < 0 || toIndex < 0) {
    return nodes;
  }
  const next = [...nodes];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) {
    return nodes;
  }
  next.splice(toIndex, 0, moved);
  return next;
}

export function EducationWorkflowBuilder({
  value,
  onChange,
}: {
  value: string;
  onChange: (next: string) => void;
}) {
  const parsed = useMemo(() => parseWorkflowContent(value), [value]);
  const [nodeOrder, setNodeOrder] = useState<WorkflowNodeId[]>(() =>
    deriveNodeOrder(parsed.content),
  );
  const [enabledStages, setEnabledStages] = useState<StageEnabledMap>(() =>
    deriveEnabledStages(parsed.content, nodeOrder),
  );
  const [cp4Enabled, setCp4Enabled] = useState<boolean>(() =>
    deriveCp4Enabled(parsed.content),
  );
  const [maxLocalRework, setMaxLocalRework] = useState<number>(() =>
    parseGuardMax(parsed.content),
  );
  const [draggingNode, setDraggingNode] = useState<WorkflowNodeId | null>(null);
  const [dragOverNode, setDragOverNode] = useState<WorkflowNodeId | null>(null);
  const [baseContent, setBaseContent] = useState<Record<string, unknown>>(
    parsed.content,
  );

  useEffect(() => {
    const order = deriveNodeOrder(parsed.content);
    setNodeOrder(order);
    setEnabledStages(deriveEnabledStages(parsed.content, order));
    setCp4Enabled(deriveCp4Enabled(parsed.content));
    setMaxLocalRework(parseGuardMax(parsed.content));
    setBaseContent(parsed.content);
  }, [parsed.content]);

  useEffect(() => {
    const next: Record<string, unknown> = { ...baseContent };

    const existingCheckpoints =
      baseContent.checkpoints && typeof baseContent.checkpoints === "object"
        ? (baseContent.checkpoints as Record<string, unknown>)
        : {};
    const existingGuard =
      baseContent.guard && typeof baseContent.guard === "object"
        ? (baseContent.guard as Record<string, unknown>)
        : {};

    next.nodes = nodeOrder.map((id) => NODE_META[id].contentToken);
    next.enabled_stages = STAGE_NODE_IDS.filter((id) => enabledStages[id]).map(
      (id) => NODE_META[id].contentToken,
    );
    next.checkpoints = {
      ...existingCheckpoints,
      "cp4-asset-extraction-confirm": cp4Enabled,
      cp4: cp4Enabled,
    };
    next.guard = {
      ...existingGuard,
      max_local_rework: maxLocalRework,
    };
    next.rerun_guard = `max_local_rework=${maxLocalRework}`;

    const serialized = JSON.stringify(next, null, 2);
    if (serialized !== value) {
      onChange(serialized);
    }
  }, [
    baseContent,
    cp4Enabled,
    enabledStages,
    maxLocalRework,
    nodeOrder,
    onChange,
    value,
  ]);

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">拖拽式流程编排</p>
        <p className="text-muted-foreground text-xs">
          拖拽调整节点顺序；通过开关控制阶段启停；设置返工护栏上限。
        </p>
        {parsed.parseError && (
          <p className="text-amber-600 text-xs">{parsed.parseError}</p>
        )}
      </div>

      <div className="space-y-2">
        {nodeOrder.map((nodeId, index) => {
          const meta = NODE_META[nodeId];
          const isStage =
            nodeId === "blueprint" ||
            nodeId === "package" ||
            nodeId === "reviewer" ||
            nodeId === "critic";
          const isEnabled = isStage
            ? enabledStages[nodeId]
            : nodeId === "cp4"
              ? cp4Enabled
              : true;
          return (
            <div
              key={nodeId}
              draggable
              className={cn(
                "bg-background flex items-center gap-3 rounded-md border p-2",
                draggingNode === nodeId && "opacity-60",
                dragOverNode === nodeId && "border-primary",
                !isEnabled && "opacity-60",
              )}
              onDragStart={() => setDraggingNode(nodeId)}
              onDragOver={(event) => {
                event.preventDefault();
                if (dragOverNode !== nodeId) {
                  setDragOverNode(nodeId);
                }
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (draggingNode) {
                  setNodeOrder((prev) =>
                    reorderNodes(prev, draggingNode, nodeId),
                  );
                }
                setDraggingNode(null);
                setDragOverNode(null);
              }}
              onDragEnd={() => {
                setDraggingNode(null);
                setDragOverNode(null);
              }}
            >
              <GripVerticalIcon className="text-muted-foreground h-4 w-4 shrink-0 cursor-grab" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{meta.label}</span>
                  <Badge variant="outline" className="text-[10px]">
                    {meta.kind}
                  </Badge>
                  <Badge variant="secondary" className="text-[10px]">
                    {index + 1}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  onClick={() =>
                    setNodeOrder((prev) => {
                      const currentIndex = prev.indexOf(nodeId);
                      if (currentIndex <= 0) {
                        return prev;
                      }
                      const targetId = prev[currentIndex - 1];
                      if (!targetId) {
                        return prev;
                      }
                      return reorderNodes(prev, nodeId, targetId);
                    })
                  }
                >
                  <ArrowUpIcon className="h-3 w-3" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  onClick={() =>
                    setNodeOrder((prev) => {
                      const currentIndex = prev.indexOf(nodeId);
                      if (currentIndex < 0 || currentIndex >= prev.length - 1) {
                        return prev;
                      }
                      const targetId = prev[currentIndex + 1];
                      if (!targetId) {
                        return prev;
                      }
                      return reorderNodes(prev, nodeId, targetId);
                    })
                  }
                >
                  <ArrowDownIcon className="h-3 w-3" />
                </Button>
              </div>
              {isStage && (
                <Switch
                  checked={enabledStages[nodeId]}
                  onCheckedChange={(checked) =>
                    setEnabledStages((prev) => ({
                      ...prev,
                      [nodeId]: Boolean(checked),
                    }))
                  }
                />
              )}
              {nodeId === "cp4" && (
                <Switch
                  checked={cp4Enabled}
                  onCheckedChange={(checked) => setCp4Enabled(Boolean(checked))}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-xs">返工上限</span>
          <Input
            className="h-8 w-24"
            inputMode="numeric"
            value={String(maxLocalRework)}
            onChange={(event) => {
              const parsedValue = Number(event.target.value);
              if (!Number.isFinite(parsedValue) || parsedValue < 0) {
                return;
              }
              setMaxLocalRework(Math.floor(parsedValue));
            }}
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setNodeOrder(DEFAULT_NODE_ORDER);
            setEnabledStages({
              blueprint: true,
              package: true,
              reviewer: true,
              critic: true,
            });
            setCp4Enabled(true);
            setMaxLocalRework(1);
          }}
        >
          <RotateCcwIcon className="mr-2 h-3.5 w-3.5" />
          恢复默认
        </Button>
      </div>
    </div>
  );
}
