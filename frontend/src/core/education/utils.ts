import type {
  CriticSummary,
  CourseArtifactManifest,
  EducationCheckpoint,
  EducationCheckpointOption,
  EducationCheckpointType,
  EducationSubtaskMeta,
  ReviewerSummary,
} from "./types";

export const EDUCATION_AGENT_NAME = "education-course-studio";

const CHECKPOINT_META: Record<
  string,
  { type: EducationCheckpointType; title: string }
> = {
  "任务确认点": {
    type: "task_confirmation",
    title: "任务确认点",
  },
  "课程目标锁定点": {
    type: "goal_lock",
    title: "课程目标锁定点",
  },
  "草案评审点": {
    type: "draft_review",
    title: "草案评审点",
  },
};

const EDUCATION_SUBTASK_RULES: Array<{
  pattern: RegExp;
  stage: string;
  label: string;
}> = [
  {
    pattern: /(stage 1|预期结果)/i,
    stage: "UbD Stage 1",
    label: "预期结果",
  },
  {
    pattern: /(research|场景资料)/i,
    stage: "Research",
    label: "场景资料",
  },
  {
    pattern: /(stage 2|证据设计)/i,
    stage: "UbD Stage 2",
    label: "证据设计",
  },
  {
    pattern: /(stage 3|pbl 活动)/i,
    stage: "UbD Stage 3",
    label: "PBL 活动",
  },
  {
    pattern: /(learning kit|学具附录)/i,
    stage: "Learning Kit",
    label: "学具附录",
  },
  {
    pattern: /(presentation|成果整合)/i,
    stage: "Presentation",
    label: "成果整合",
  },
  {
    pattern: /(reviewer|课程质量评审|质量评审)/i,
    stage: "Reviewer",
    label: "质量评审",
  },
  {
    pattern: /(critic|挑战性复核|复核)/i,
    stage: "Critic",
    label: "挑战复核",
  },
];

function stripLeadingMarker(line: string) {
  return line.replace(/^[^A-Za-z0-9\u4e00-\u9fa5\[]+/, "").trim();
}

function parseCheckpointHeading(line: string) {
  const cleaned = stripLeadingMarker(line);
  const match = /^(任务确认点|课程目标锁定点|草案评审点)\s*[:：]?\s*(.*)$/u.exec(
    cleaned,
  );
  if (!match) {
    return null;
  }

  const label = match[1];
  if (!label) {
    return null;
  }
  const remainder = match[2]?.trim();
  const meta = CHECKPOINT_META[label];
  if (!meta) {
    return null;
  }

  return {
    ...meta,
    remainder,
  };
}

function parseCheckpointOptions(lines: string[]): EducationCheckpointOption[] {
  return lines
    .map((line) => {
      const match = /^\s*(\d+)\.\s+(.+)$/u.exec(line);
      if (!match) {
        return null;
      }

      const label = match[2];
      if (!label) {
        return null;
      }

      return {
        index: Number(match[1]),
        label: label.trim(),
        value: label.trim(),
      };
    })
    .filter((option): option is EducationCheckpointOption => option !== null);
}

function parseCheckpointMetadata(lines: string[]) {
  const questionLines: string[] = [];
  const detailsLines: string[] = [];
  let checkpoint_id: string | undefined;
  let checkpoint_type: string | undefined;
  let summary: string | undefined;
  let recommended_option: string | undefined;
  let retry_target: string | undefined;
  let inDetails = false;

  for (const line of lines) {
    const metaMatch = /^([a-z_]+)\s*:\s*(.+)$/iu.exec(line);
    if (metaMatch) {
      const key = metaMatch[1]?.toLowerCase();
      const value = metaMatch[2]?.trim();
      if (!value) {
        continue;
      }

      if (key === "checkpoint_id") {
        checkpoint_id = value;
        inDetails = false;
        continue;
      }
      if (key === "checkpoint_type") {
        checkpoint_type = value;
        inDetails = false;
        continue;
      }
      if (key === "summary") {
        summary = value;
        inDetails = false;
        continue;
      }
      if (key === "recommended_option") {
        recommended_option = value;
        inDetails = false;
        continue;
      }
      if (key === "retry_target") {
        retry_target = value;
        inDetails = false;
        continue;
      }
      if (key === "details") {
        detailsLines.push(value);
        inDetails = true;
        continue;
      }
    }

    if (inDetails) {
      detailsLines.push(line);
      continue;
    }

    questionLines.push(line);
  }

  return {
    questionLines,
    checkpoint_id,
    checkpoint_type,
    summary,
    recommended_option,
    retry_target,
    details: detailsLines.length > 0 ? detailsLines.join(" ").trim() : undefined,
  };
}

export function isEducationAgent(agentName?: string | null) {
  return agentName === EDUCATION_AGENT_NAME;
}

export function getEducationPromptTemplate() {
  return [
    "课程主题：",
    "适用年级：",
    "课时数：",
    "课程方向：人工智能教育 / 科学教育 / 融合",
    "UbD重点：大概念 / 核心问题 / 迁移目标",
    "PBL重点：驱动性问题 / 项目成果 / 小组方式",
    "学具要求：需要 / 不需要；材料或安全限制",
    "补充说明：",
  ].join("\n");
}

export function parseEducationCheckpoint(
  content: string,
): EducationCheckpoint | null {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return null;
  }

  const optionLines = lines.filter((line) => /^\s*\d+\.\s+/.test(line));
  const options = parseCheckpointOptions(optionLines);
  if (options.length === 0) {
    return null;
  }

  const bodyLines = lines.filter((line) => !/^\s*\d+\.\s+/.test(line));
  if (bodyLines.length === 0) {
    return null;
  }

  const firstLine = bodyLines[0];
  if (!firstLine) {
    return null;
  }

  const heading = parseCheckpointHeading(firstLine);
  if (!heading) {
    return null;
  }

  const metadata = parseCheckpointMetadata(bodyLines.slice(1));
  const context = heading.remainder ?? undefined;
  const questionText = metadata.questionLines.join(" ").trim();
  const question =
    questionText.length > 0 ? questionText : (context ?? heading.title);

  return {
    type: heading.type,
    title: heading.title,
    checkpoint_type: metadata.checkpoint_type,
    context,
    summary: metadata.summary,
    question,
    checkpoint_id: metadata.checkpoint_id,
    recommended_option: metadata.recommended_option,
    retry_target: metadata.retry_target,
    details: metadata.details,
    options,
    rawContent: content,
  };
}

export function parseCourseArtifactManifest(
  value: unknown,
): CourseArtifactManifest | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const manifest = value as Record<string, unknown>;
  if (typeof manifest.title !== "string" || !Array.isArray(manifest.artifacts)) {
    return null;
  }

  const artifacts: CourseArtifactManifest["artifacts"] = [];
  for (const artifact of manifest.artifacts) {
    if (!artifact || typeof artifact !== "object") {
      continue;
    }

    const entry = artifact as Record<string, unknown>;
    if (typeof entry.label !== "string" || typeof entry.path !== "string") {
      continue;
    }

    artifacts.push({
      label: entry.label,
      path: entry.path,
      description:
        typeof entry.description === "string" ? entry.description : undefined,
    });
  }

  if (artifacts.length === 0) {
    return null;
  }

  return {
    title: manifest.title,
    summary:
      typeof manifest.summary === "string" ? manifest.summary : undefined,
    artifacts,
  };
}

function parseStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

export function parseReviewerSummary(value: unknown): ReviewerSummary | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const summary = value as Record<string, unknown>;
  if (typeof summary.verdict !== "string") {
    return null;
  }

  const hardGates: ReviewerSummary["hard_gates"] = [];
  if (Array.isArray(summary.hard_gates)) {
    for (const gate of summary.hard_gates) {
      if (!gate || typeof gate !== "object") {
        continue;
      }
      const entry = gate as Record<string, unknown>;
      if (typeof entry.name !== "string" || typeof entry.status !== "string") {
        continue;
      }
      hardGates.push({
        name: entry.name,
        status: entry.status,
        note: typeof entry.note === "string" ? entry.note : undefined,
      });
    }
  }

  const rubricScores: ReviewerSummary["rubric_scores"] = [];
  if (Array.isArray(summary.rubric_scores)) {
    for (const score of summary.rubric_scores) {
      if (!score || typeof score !== "object") {
        continue;
      }
      const entry = score as Record<string, unknown>;
      if (
        typeof entry.dimension !== "string" ||
        typeof entry.score !== "number" ||
        !Number.isFinite(entry.score)
      ) {
        continue;
      }

      rubricScores.push({
        dimension: entry.dimension,
        is_hard_gate:
          typeof entry.is_hard_gate === "boolean"
            ? entry.is_hard_gate
            : undefined,
        score: Math.max(0, Math.min(3, Math.round(entry.score))),
        status: typeof entry.status === "string" ? entry.status : undefined,
        note: typeof entry.note === "string" ? entry.note : undefined,
      });
    }
  }

  return {
    verdict: summary.verdict,
    hard_gates: hardGates,
    key_issues: parseStringArray(summary.key_issues),
    rubric_scores: rubricScores,
    suggested_rerun_agents: parseStringArray(summary.suggested_rerun_agents),
    lead_note: typeof summary.lead_note === "string" ? summary.lead_note : undefined,
  };
}

export function parseCriticSummary(value: unknown): CriticSummary | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const summary = value as Record<string, unknown>;
  if (
    typeof summary.verdict !== "string" ||
    typeof summary.agreement_with_reviewer !== "string"
  ) {
    return null;
  }

  return {
    verdict: summary.verdict,
    agreement_with_reviewer: summary.agreement_with_reviewer,
    new_key_risks: parseStringArray(summary.new_key_risks),
    escalate_rerun:
      typeof summary.escalate_rerun === "boolean"
        ? summary.escalate_rerun
        : undefined,
    suggested_rerun_agents: parseStringArray(summary.suggested_rerun_agents),
    lead_note:
      typeof summary.lead_note === "string" ? summary.lead_note : undefined,
  };
}

export function getEducationSubtaskMeta(
  description: string,
  prompt: string,
): EducationSubtaskMeta | null {
  const text = `${description}\n${prompt}`;
  const rule = EDUCATION_SUBTASK_RULES.find(({ pattern }) => pattern.test(text));

  if (!rule) {
    return null;
  }

  return {
    stage: rule.stage,
    label: rule.label,
  };
}
