"use client";

import {
  ClipboardCheckIcon,
  FileCheck2Icon,
  TargetIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { urlOfArtifact } from "@/core/artifacts/utils";
import {
  parseCriticSummary,
  parseReviewerSummary,
  type CriticSummary,
  type EducationCheckpoint,
  type ReviewerSummary,
} from "@/core/education";
import { cn } from "@/lib/utils";

const CHECKPOINT_ICON = {
  task_confirmation: ClipboardCheckIcon,
  goal_lock: TargetIcon,
  draft_review: FileCheck2Icon,
} as const;

export function EducationCheckpointCard({
  checkpoint,
  threadId,
  disabled = false,
  onSelect,
}: {
  checkpoint: EducationCheckpoint;
  threadId: string;
  disabled?: boolean;
  onSelect: (
    value: string,
    checkpoint: EducationCheckpoint,
  ) => Promise<void> | void;
}) {
  const [pendingValue, setPendingValue] = useState<string | null>(null);
  const [reviewerSummary, setReviewerSummary] = useState<ReviewerSummary | null>(
    null,
  );
  const [criticSummary, setCriticSummary] = useState<CriticSummary | null>(null);

  const Icon = useMemo(
    () => CHECKPOINT_ICON[checkpoint.type],
    [checkpoint.type],
  );

  useEffect(() => {
    if (checkpoint.type !== "draft_review") {
      setReviewerSummary(null);
      setCriticSummary(null);
      return;
    }

    let cancelled = false;

    async function loadReviewerSummary() {
      try {
        const [reviewerResponse, criticResponse] = await Promise.all([
          fetch(
            urlOfArtifact({
              filepath: "/mnt/user-data/workspace/reviewer-summary.json",
              threadId,
            }),
          ),
          fetch(
            urlOfArtifact({
              filepath: "/mnt/user-data/workspace/critic-summary.json",
              threadId,
            }),
          ),
        ]);

        if (!cancelled && reviewerResponse.ok) {
          const reviewerRaw = (await reviewerResponse.json()) as unknown;
          setReviewerSummary(parseReviewerSummary(reviewerRaw));
        }
        if (!cancelled && criticResponse.ok) {
          const criticRaw = (await criticResponse.json()) as unknown;
          setCriticSummary(parseCriticSummary(criticRaw));
        }
      } catch {
        if (!cancelled) {
          setReviewerSummary(null);
          setCriticSummary(null);
        }
      }
    }

    void loadReviewerSummary();

    return () => {
      cancelled = true;
    };
  }, [checkpoint.type, threadId]);

  async function handleSelect(value: string) {
    setPendingValue(value);
    try {
      await onSelect(value, checkpoint);
    } finally {
      setPendingValue(null);
    }
  }

  function isRecommendedOption(value: string, index: number) {
    if (!checkpoint.recommended_option) {
      return false;
    }
    const normalized = checkpoint.recommended_option.trim();
    if (/^\d+$/u.test(normalized)) {
      return Number(normalized) === index;
    }
    return normalized === value;
  }

  const failedHardGates = reviewerSummary?.hard_gates.filter(
    (gate) => gate.status.toLowerCase() === "fail",
  );
  const hasReviewerCriticConflict =
    criticSummary?.agreement_with_reviewer === "conflict";

  return (
    <Card className="bg-background/80 w-full gap-4 border-dashed">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-full">
            <Icon className="text-primary h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base">{checkpoint.title}</CardTitle>
            {checkpoint.context && (
              <p className="text-muted-foreground mt-1 text-sm">
                {checkpoint.context}
              </p>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-6">{checkpoint.question}</p>
        {checkpoint.summary && (
          <div className="bg-muted/50 rounded-lg border p-3 text-sm leading-6">
            {checkpoint.summary}
          </div>
        )}
        {checkpoint.details && (
          <div className="bg-muted/50 rounded-lg border p-3 text-sm leading-6">
            {checkpoint.details}
          </div>
        )}
        {checkpoint.retry_target && (
          <p className="text-muted-foreground text-xs">
            建议回退对象：{checkpoint.retry_target}
          </p>
        )}
        {reviewerSummary && (
          <div className="bg-muted/50 space-y-2 rounded-lg border p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">Reviewer 结论</Badge>
              <span>{reviewerSummary.verdict}</span>
              {failedHardGates && failedHardGates.length > 0 && (
                <Badge variant="destructive">
                  硬门槛风险 {failedHardGates.length}
                </Badge>
              )}
            </div>
            {reviewerSummary.key_issues.length > 0 && (
              <p className="text-muted-foreground text-xs leading-5">
                关键问题：{reviewerSummary.key_issues.slice(0, 3).join("；")}
              </p>
            )}
          </div>
        )}
        {criticSummary && (
          <div className="bg-muted/50 space-y-2 rounded-lg border p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">Critic 复核</Badge>
              <span>{criticSummary.verdict}</span>
              {hasReviewerCriticConflict && (
                <Badge variant="destructive">与 Reviewer 存在冲突</Badge>
              )}
              {criticSummary.escalate_rerun && (
                <Badge variant="destructive">建议升级返工</Badge>
              )}
            </div>
            {criticSummary.new_key_risks.length > 0 && (
              <p className="text-muted-foreground text-xs leading-5">
                新增风险：{criticSummary.new_key_risks.slice(0, 3).join("；")}
              </p>
            )}
          </div>
        )}
        <div className="flex flex-col gap-2">
          {checkpoint.options.map((option) => {
            const isPending = pendingValue === option.value;
            const isRecommended = isRecommendedOption(
              option.value,
              option.index,
            );
            return (
              <Button
                key={`${checkpoint.type}-${option.index}`}
                className={cn("justify-start whitespace-normal text-left")}
                disabled={disabled || pendingValue !== null}
                variant={isPending || isRecommended ? "default" : "outline"}
                onClick={() => void handleSelect(option.value)}
              >
                <span>{option.label}</span>
                {isRecommended && (
                  <Badge className="ml-2" variant="secondary">
                    推荐
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
