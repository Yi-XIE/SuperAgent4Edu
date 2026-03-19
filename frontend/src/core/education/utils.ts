import type {
  CriticSummary,
  CourseArtifactManifest,
  EducationCheckpoint,
  EducationCheckpointOption,
  EducationCheckpointType,
  EducationGenerationModeCard,
  EducationStarterMode,
  EducationSubtaskMeta,
  EducationTaskBriefCard,
  ReviewerSummary,
  GenerationMode,
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
  "课程蓝图锁定点": {
    type: "goal_lock",
    title: "课程蓝图锁定点",
  },
  "课程目标锁定点": {
    type: "goal_lock",
    title: "课程蓝图锁定点",
  },
  "草案评审点": {
    type: "draft_review",
    title: "草案评审点",
  },
  "素材提取确认": {
    type: "asset_extraction_confirm",
    title: "素材提取确认",
  },
};

const CHECKPOINT_ID_BY_TYPE: Record<EducationCheckpointType, string> = {
  task_confirmation: "cp1-task-confirmation",
  goal_lock: "cp2-goal-lock",
  draft_review: "cp3-draft-review",
  asset_extraction_confirm: "cp4-asset-extraction-confirm",
};

const EDUCATION_SUBTASK_RULES: Array<{
  pattern: RegExp;
  stage: string;
  label: string;
}> = [
  {
    pattern: /(task brief|任务简报|blueprint|课程蓝图|stage 1|预期结果|research|场景资料)/i,
    stage: "Blueprint",
    label: "课程蓝图",
  },
  {
    pattern: /(package|完整课包|stage 2|stage 3|证据设计|pbl 活动|learning kit|学具附录|presentation|成果整合)/i,
    stage: "Package",
    label: "完整课包",
  },
  {
    pattern: /(reviewer|课程质量评审|质量评审)/i,
    stage: "Reviewer",
    label: "质量评审",
  },
  {
    pattern: /(critic|挑战性复核|复核|严格复核)/i,
    stage: "Critic",
    label: "挑战复核",
  },
  {
    pattern: /(asset retrieval|asset extraction|素材召回|素材提取)/i,
    stage: "Assets",
    label: "素材沉淀",
  },
];

function stripLeadingMarker(line: string) {
  return line.replace(/^[^A-Za-z0-9\u4e00-\u9fa5\[]+/, "").trim();
}

const TASK_BRIEF_FIELD_LABELS: Record<string, string> = {
  course_topic: "课程主题",
  grade_or_level: "适用年级",
  session_count: "课时数",
  domain_focus: "课程方向",
  pbl: "PBL 要求",
  learning_kit: "学具要求",
  existing_assets: "已有素材",
  teacher_notes: "补充说明",
};

const GENERATION_MODE_LABELS: Record<GenerationMode, string> = {
  from_scratch: "从零生成",
  material_first: "优先吸收已有素材",
  mixed: "混合模式",
};

function parseCheckpointHeading(line: string) {
  const cleaned = stripLeadingMarker(line);
  const match = /^(任务确认点|课程蓝图锁定点|课程目标锁定点|草案评审点|素材提取确认)\s*[:：]?\s*(.*)$/u.exec(
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
    "生成策略：from_scratch / material_first / mixed",
    "课程方向：人工智能教育 / 科学教育 / 融合",
    "UbD重点：大概念 / 核心问题 / 迁移目标",
    "PBL重点：驱动性问题 / 项目成果 / 小组方式",
    "学具要求：需要 / 不需要；材料或安全限制",
    "补充说明：",
  ].join("\n");
}

export function buildEducationStarterPrompt(mode: EducationStarterMode) {
  if (mode === "quick_generate") {
    return [
      "【入口】快速生成课包",
      "请先根据以下信息生成任务简报卡，再给出生成策略确认卡，等我确认后再继续课程蓝图。",
      "课程主题：",
      "适用年级：",
      "课时数：",
      "课程方向：",
      "学具要求：",
      "补充说明：",
    ].join("\n");
  }

  return [
    "【入口】带着已有想法生成",
    "请先吸收我的已有想法，整理成任务简报卡，再给出生成策略确认卡，等我确认后再继续课程蓝图。",
    "课程主题：",
    "适用年级：",
    "课时数：",
    "我已有的目标或想法：",
    "我已有的活动点子：",
    "学具限制：",
    "已有素材：",
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
    checkpoint_id:
      metadata.checkpoint_id ?? CHECKPOINT_ID_BY_TYPE[heading.type],
    recommended_option: metadata.recommended_option,
    retry_target: metadata.retry_target,
    details: metadata.details,
    options,
    rawContent: content,
  };
}

export function parseEducationTaskBriefCard(
  content: string,
): EducationTaskBriefCard | null {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return null;
  }

  const headingMatch = /^(任务简报卡|任务简报)\s*[:：]?\s*(.*)$/u.exec(
    stripLeadingMarker(lines[0] ?? ""),
  );
  if (!headingMatch) {
    return null;
  }

  const headingTitle = headingMatch[2]?.trim();
  const title =
    headingTitle && headingTitle.length > 0 ? headingTitle : "任务简报卡";
  let summary: string | undefined;
  const actions: string[] = [];
  const fields: EducationTaskBriefCard["fields"] = [];

  for (const line of lines.slice(1)) {
    const match = /^([a-z_]+)\s*:\s*(.+)$/iu.exec(line);
    if (!match) {
      continue;
    }
    const key = match[1]?.toLowerCase();
    const value = match[2]?.trim();
    if (!key || !value) {
      continue;
    }
    if (key === "summary") {
      summary = value;
      continue;
    }
    if (key === "actions") {
      actions.push(
        ...value
          .split(/[|｜]/u)
          .map((item) => item.trim())
          .filter(Boolean),
      );
      continue;
    }

    const label = TASK_BRIEF_FIELD_LABELS[key];
    if (label) {
      fields.push({ key, label, value });
    }
  }

  if (fields.length === 0 && !summary) {
    return null;
  }

  return {
    title,
    summary,
    fields,
    actions,
    rawContent: content,
  };
}

export function parseEducationGenerationModeCard(
  content: string,
): EducationGenerationModeCard | null {
  const lines = content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    return null;
  }

  const headingMatch = /^(生成策略确认卡|生成策略确认|生成策略)\s*[:：]?\s*(.*)$/u.exec(
    stripLeadingMarker(lines[0] ?? ""),
  );
  if (!headingMatch) {
    return null;
  }

  const headingTitle = headingMatch[2]?.trim();
  const title =
    headingTitle && headingTitle.length > 0 ? headingTitle : "生成策略确认卡";
  let summary: string | undefined;
  let recommended_mode: GenerationMode | undefined;
  let retrieval_hint: string | undefined;
  const options: EducationGenerationModeCard["options"] = [];

  for (const line of lines.slice(1)) {
    const match = /^([a-z_]+)\s*:\s*(.+)$/iu.exec(line);
    if (!match) {
      continue;
    }
    const key = match[1]?.toLowerCase();
    const value = match[2]?.trim();
    if (!key || !value) {
      continue;
    }

    if (key === "summary") {
      summary = value;
      continue;
    }
    if (key === "recommended_mode") {
      if (
        value === "from_scratch" ||
        value === "material_first" ||
        value === "mixed"
      ) {
        recommended_mode = value;
      }
      continue;
    }
    if (key === "retrieval_hint") {
      retrieval_hint = value;
      continue;
    }
    if (
      key === "from_scratch" ||
      key === "material_first" ||
      key === "mixed"
    ) {
      options.push({
        mode: key,
        description: value,
      });
    }
  }

  if (options.length === 0 && !summary && !recommended_mode) {
    return null;
  }

  return {
    title,
    summary,
    recommended_mode,
    retrieval_hint,
    options:
      options.length > 0
        ? options
        : (Object.keys(GENERATION_MODE_LABELS) as GenerationMode[]).map(
            (mode) => ({
              mode,
              description: GENERATION_MODE_LABELS[mode],
            }),
          ),
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
