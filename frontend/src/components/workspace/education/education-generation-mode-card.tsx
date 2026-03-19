"use client";

import { CompassIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  type EducationGenerationModeCard as EducationGenerationModeCardData,
  type GenerationMode,
} from "@/core/education";

const MODE_LABELS: Record<GenerationMode, string> = {
  from_scratch: "从零生成",
  material_first: "优先吸收已有素材",
  mixed: "混合模式",
};

function buildGenerationModeDraft(card: EducationGenerationModeCardData) {
  const lines = [`${card.title}: 已确认生成策略`];
  if (card.summary) {
    lines.push(`summary: ${card.summary}`);
  }
  if (card.recommended_mode) {
    lines.push(`recommended_mode: ${card.recommended_mode}`);
  }
  if (card.retrieval_hint) {
    lines.push(`retrieval_hint: ${card.retrieval_hint}`);
  }
  for (const mode of ["from_scratch", "material_first", "mixed"] as const) {
    const option = card.options.find((item) => item.mode === mode);
    if (option?.description) {
      lines.push(`${mode}: ${option.description}`);
    }
  }
  return lines.join("\n");
}

export function EducationGenerationModeCard({
  card,
  editable = false,
  disabled = false,
  onApply,
}: {
  card: EducationGenerationModeCardData;
  editable?: boolean;
  disabled?: boolean;
  onApply?: (content: string) => void;
}) {
  const initialDraft = useMemo(() => buildGenerationModeDraft(card), [card]);
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(initialDraft);

  useEffect(() => {
    if (!isEditing) {
      setDraft(initialDraft);
    }
  }, [initialDraft, isEditing]);

  return (
    <Card className="w-full gap-4 border-dashed">
      <CardHeader className="gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-10 w-10 items-center justify-center rounded-full">
            <CompassIcon className="text-primary h-5 w-5" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-base">{card.title}</CardTitle>
            {card.summary && (
              <p className="text-muted-foreground text-sm">{card.summary}</p>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {editable && onApply && !isEditing && (
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={disabled}
              size="sm"
              variant="secondary"
              onClick={() => onApply(initialDraft)}
            >
              一键回填对话
            </Button>
            <Button
              disabled={disabled}
              size="sm"
              variant="outline"
              onClick={() => {
                setDraft(initialDraft);
                setIsEditing(true);
              }}
            >
              编辑后回填
            </Button>
          </div>
        )}
        {editable && onApply && isEditing && (
          <div className="space-y-3">
            <Textarea
              className="min-h-40"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={disabled || !draft.trim()}
                size="sm"
                onClick={() => {
                  onApply(draft.trim());
                  setIsEditing(false);
                }}
              >
                回填对话
              </Button>
              <Button
                disabled={disabled}
                size="sm"
                variant="outline"
                onClick={() => {
                  setDraft(initialDraft);
                  setIsEditing(false);
                }}
              >
                取消编辑
              </Button>
            </div>
          </div>
        )}
        {card.recommended_mode && (
          <div className="flex items-center gap-2 text-sm">
            <Badge>推荐</Badge>
            <span>{MODE_LABELS[card.recommended_mode]}</span>
          </div>
        )}
        {card.retrieval_hint && (
          <div className="bg-muted/40 rounded-lg border p-3 text-sm leading-6">
            {card.retrieval_hint}
          </div>
        )}
        <div className="grid gap-3">
          {card.options.map((option) => (
            <div key={option.mode} className="rounded-lg border p-3">
              <p className="text-sm font-medium">{MODE_LABELS[option.mode]}</p>
              <p className="text-muted-foreground mt-1 text-sm leading-6">
                {option.description}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
