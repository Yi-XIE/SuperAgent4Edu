"use client";

import { ClipboardListIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { type EducationTaskBriefCard as EducationTaskBriefCardData } from "@/core/education";

function buildTaskBriefDraft(card: EducationTaskBriefCardData) {
  const lines = [`${card.title}: 已确认任务简报`];
  if (card.summary) {
    lines.push(`summary: ${card.summary}`);
  }
  for (const field of card.fields) {
    lines.push(`${field.key}: ${field.value}`);
  }
  if (card.actions.length > 0) {
    lines.push(`actions: ${card.actions.join(" | ")}`);
  }
  return lines.join("\n");
}

export function EducationTaskBriefCard({
  card,
  editable = false,
  disabled = false,
  onApply,
}: {
  card: EducationTaskBriefCardData;
  editable?: boolean;
  disabled?: boolean;
  onApply?: (content: string) => void;
}) {
  const initialDraft = useMemo(() => buildTaskBriefDraft(card), [card]);
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
            <ClipboardListIcon className="text-primary h-5 w-5" />
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
        {card.fields.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {card.fields.map((field) => (
              <div
                key={`${field.key}-${field.value}`}
                className="bg-muted/40 rounded-lg border p-3"
              >
                <p className="text-muted-foreground text-xs">{field.label}</p>
                <p className="mt-1 text-sm leading-6">{field.value}</p>
              </div>
            ))}
          </div>
        )}
        {card.actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {card.actions.map((action) => (
              <Badge key={action} variant="secondary">
                {action}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
