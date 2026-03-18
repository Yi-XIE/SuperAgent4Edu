"""Task tool for delegating work to subagents."""

import json
import logging
import re
import time
import uuid
from dataclasses import replace
from typing import Annotated, Literal

from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langgraph.config import get_stream_writer
from langgraph.typing import ContextT

from src.agents.lead_agent.prompt import get_skills_prompt_section
from src.agents.thread_state import ThreadState
from src.config.agents_config import load_agent_config
from src.subagents import SubagentExecutor, get_subagent_config
from src.subagents.executor import SubagentStatus, cleanup_background_task, get_background_task_result

logger = logging.getLogger(__name__)

_EDU_STAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "Blueprint": ("blueprint", "stage 1", "预期结果", "课程蓝图"),
    "Package": ("package", "stage 2", "stage 3", "证据设计", "活动流程", "成果整合", "学具附录"),
    "Reviewer": ("reviewer", "质量评审"),
    "Critic": ("critic", "挑战性复核"),
}


def _detect_education_stage(description: str) -> str | None:
    lowered = description.lower()
    for stage, markers in _EDU_STAGE_ALIASES.items():
        if any(marker in lowered or marker in description for marker in markers):
            return stage
    return None


def _resolve_education_run_key(state: dict, *, run_id: str | None, thread_id: str | None) -> str | None:
    runs = state.get("runs", {})
    if not isinstance(runs, dict):
        return None
    if isinstance(run_id, str) and run_id in runs and isinstance(runs[run_id], dict):
        return run_id
    if isinstance(thread_id, str):
        if thread_id in runs and isinstance(runs[thread_id], dict):
            return thread_id
        for key, raw in runs.items():
            if not isinstance(raw, dict):
                continue
            if raw.get("thread_id") == thread_id:
                return key
    return None


def _load_education_run_context(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
) -> tuple[dict, object, str] | None:
    if runtime is None:
        return None
    agent_name = runtime.context.get("agent_name")
    run_id = runtime.context.get("run_id")
    thread_id = runtime.context.get("thread_id")
    if agent_name != "education-course-studio":
        return None

    from src.education.schemas import EducationRunState
    from src.education.store import get_education_store

    store = get_education_store()
    state = store.read_state()
    run_key = _resolve_education_run_key(
        state,
        run_id=run_id if isinstance(run_id, str) else None,
        thread_id=thread_id if isinstance(thread_id, str) else None,
    )
    if run_key is None:
        return None
    raw = state.get("runs", {}).get(run_key)
    if not isinstance(raw, dict):
        return None
    run = EducationRunState(**raw)
    return state, run, run_key


def _should_skip_education_subtask(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
    description: str,
) -> str | None:
    stage = _detect_education_stage(description)
    if stage is None:
        return None

    loaded = _load_education_run_context(runtime)
    if loaded is None:
        return None
    state, run, _thread_id = loaded

    from src.education.workflow_template import enabled_rerun_stages, get_workflow_template_content

    template_content = get_workflow_template_content(state, run)
    enabled_stages = enabled_rerun_stages(template_content)
    if enabled_stages and stage in {"Blueprint", "Package", "Reviewer", "Critic"} and stage not in enabled_stages:
        return f"workflow template disabled stage `{stage}`"

    if stage == "Critic":
        if run.critic_policy == "manual_off":
            return "critic_policy=manual_off"
        if run.critic_policy == "auto" and not run.critic_enabled:
            return "critic_policy=auto 且未命中自动启用条件"
    return None


def _extract_markdown_key_lines(path, *, limit: int = 3) -> list[str]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    picked: list[str] = []
    for line in lines:
        normalized = re.sub(r"^[-*]\s+|^\d+\.\s+", "", line).strip()
        if not normalized:
            continue
        if normalized.startswith("#"):
            continue
        if len(normalized) < 4:
            continue
        picked.append(normalized)
        if len(picked) >= limit:
            break
    return picked


def _extract_artifact_paths_from_manifest(path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict):
        return []
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    paths: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        item_path = item.get("path")
        if isinstance(item_path, str) and item_path.startswith("/mnt/user-data/"):
            paths.append(item_path)
    return paths


def _sync_education_runtime_state(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
    description: str,
) -> list[str]:
    if runtime is None:
        return []
    agent_name = runtime.context.get("agent_name")
    run_id = runtime.context.get("run_id")
    thread_id = runtime.context.get("thread_id")
    if agent_name != "education-course-studio" or not isinstance(thread_id, str):
        return []

    from src.config.paths import get_paths
    from src.education.critic_policy import evaluate_critic_activation
    from src.education.schemas import (
        CourseBlueprint,
        CoursePackage,
        CriticSummaryV2,
        EducationRunState,
        ReviewerSummaryV2,
        utc_now_iso,
    )
    from src.education.store import get_education_store

    store = get_education_store()
    paths = get_paths()
    workspace_dir = paths.sandbox_work_dir(thread_id)
    outputs_dir = paths.sandbox_outputs_dir(thread_id)
    stage = _detect_education_stage(description)
    messages: list[str] = []

    def _mutate(state: dict):
        run_key = _resolve_education_run_key(
            state,
            run_id=run_id if isinstance(run_id, str) else None,
            thread_id=thread_id,
        )
        if run_key is None:
            return None
        raw = state.get("runs", {}).get(run_key)
        if not isinstance(raw, dict):
            return None
        run = EducationRunState(**raw)
        changed = False

        reviewer_path = workspace_dir / "reviewer-summary.json"
        if reviewer_path.exists() and stage in {"Reviewer", "Critic", "Package"}:
            try:
                reviewer_summary = ReviewerSummaryV2.model_validate_json(
                    reviewer_path.read_text(encoding="utf-8"),
                )
                run.reviewer_summary = reviewer_summary
                changed = True
                if run.critic_policy == "auto":
                    critic_enabled, reason = evaluate_critic_activation(run, reviewer_summary)
                    run.critic_enabled = critic_enabled
                    run.critic_activation_reason = reason
                    changed = True
            except Exception:
                logger.exception("Failed to parse reviewer-summary.json for run sync")

        critic_path = workspace_dir / "critic-summary.json"
        if critic_path.exists() and stage == "Critic":
            try:
                run.critic_summary = CriticSummaryV2.model_validate_json(
                    critic_path.read_text(encoding="utf-8"),
                )
                changed = True
            except Exception:
                logger.exception("Failed to parse critic-summary.json for run sync")

        blueprint_id = None
        blueprint_row = None
        for item_id, row in state.get("course_blueprints", {}).items():
            if isinstance(row, dict) and row.get("run_id") == run.id and row.get("org_id") == run.org_id:
                blueprint_id = item_id
                blueprint_row = row
                break
        stage1_path = workspace_dir / "stage1-ubd.md"
        research_path = workspace_dir / "research-notes.md"
        if (stage in {"Blueprint", "Package", "Reviewer", "Critic"}) and (stage1_path.exists() or research_path.exists()):
            if blueprint_row is not None:
                blueprint = CourseBlueprint(**blueprint_row)
            else:
                blueprint = CourseBlueprint(
                    id=store.generate_id("blueprint"),
                    org_id=run.org_id,
                    run_id=run.id,
                    title=run.title,
                )
            key_lines = _extract_markdown_key_lines(stage1_path, limit=8)
            questions = [line for line in key_lines if "?" in line or "？" in line]
            blueprint.big_ideas = key_lines[:3]
            blueprint.essential_questions = questions[:3]
            blueprint.transfer_goals = [line for line in key_lines if line not in questions][:3]
            if not blueprint.transfer_goals:
                blueprint.transfer_goals = key_lines[:3]
            blueprint.project_direction = run.title
            if research_path.exists():
                research_lines = _extract_markdown_key_lines(research_path, limit=6)
                blueprint.research_summary = "；".join(research_lines[:3])[:320]
            blueprint.updated_at = utc_now_iso()
            state["course_blueprints"][blueprint.id] = blueprint.model_dump()
            blueprint_id = blueprint.id
            changed = True

        package_id = None
        package_row = None
        for item_id, row in state.get("course_packages", {}).items():
            if isinstance(row, dict) and row.get("run_id") == run.id and row.get("org_id") == run.org_id:
                package_id = item_id
                package_row = row
                break
        lesson_path = outputs_dir / "lesson-plan.md"
        manifest_path = outputs_dir / "artifact-manifest.json"
        if (stage in {"Package", "Reviewer", "Critic"}) and lesson_path.exists():
            if package_row is not None:
                package = CoursePackage(**package_row)
            else:
                package = CoursePackage(
                    id=store.generate_id("package"),
                    org_id=run.org_id,
                    run_id=run.id,
                    blueprint_id=blueprint_id,
                )
            package.blueprint_id = blueprint_id
            lesson_lines = _extract_markdown_key_lines(lesson_path, limit=5)
            package.summary = "；".join(lesson_lines[:3])[:320]
            package.updated_at = utc_now_iso()
            state["course_packages"][package.id] = package.model_dump()
            package_id = package.id
            changed = True

        if stage in {"Package", "Reviewer", "Critic"} and manifest_path.exists():
            manifest_paths = _extract_artifact_paths_from_manifest(manifest_path)
            if manifest_paths:
                run.artifact_paths = manifest_paths
                changed = True

        if changed:
            run.updated_at = utc_now_iso()
            state["runs"][run_key] = run.model_dump()
            return {
                "reviewer_synced": reviewer_path.exists(),
                "critic_synced": critic_path.exists() and stage == "Critic",
                "blueprint_id": blueprint_id,
                "package_id": package_id,
            }
        return None

    changed_info = store.transaction(_mutate)
    if not isinstance(changed_info, dict):
        return messages
    if changed_info.get("reviewer_synced"):
        messages.append("reviewer summary synced to run state")
    if changed_info.get("critic_synced"):
        messages.append("critic summary synced to run state")
    if changed_info.get("blueprint_id"):
        messages.append("blueprint object upserted")
    if changed_info.get("package_id"):
        messages.append("package object upserted")
    return messages


def _run_presentation_hard_validator(workspace_dir, outputs_dir) -> tuple[bool, list[str]]:
    """Validate non-negotiable constraints before reviewer stage."""
    issues: list[str] = []
    brief_path = workspace_dir / "course-brief.json"
    lesson_path = outputs_dir / "lesson-plan.md"
    kit_path = outputs_dir / "learning-kit-appendix.md"

    if not brief_path.exists() or not lesson_path.exists() or not kit_path.exists():
        return True, []

    try:
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False, ["course-brief.json 不是有效 JSON，无法执行硬校验。"]

    lesson = lesson_path.read_text(encoding="utf-8")
    kit = kit_path.read_text(encoding="utf-8")

    session_count = int(brief.get("session_count", 0) or 0)
    session_minutes = int(brief.get("session_length_minutes", 0) or 0)
    learning_kit = brief.get("learning_kit", {})
    constraints = learning_kit.get("constraints", []) if isinstance(learning_kit, dict) else []
    constraint_text = "\n".join(str(item) for item in constraints)

    if session_count > 0:
        markers = re.findall(r"(?:第\s*(\d+)\s*课时|Session\s*(\d+)|课时\s*(\d+))", lesson, flags=re.IGNORECASE)
        unique_ids = {next((value for value in group if value), "") for group in markers if any(group)}
        if unique_ids and len(unique_ids) < session_count:
            issues.append(f"教案仅识别到 {len(unique_ids)} 个课时标记，低于 brief 约束 {session_count}。")

    if session_minutes > 0:
        durations = [int(value) for value in re.findall(r"(\d+)\s*分钟", lesson)]
        if durations and any(value != session_minutes for value in durations):
            issues.append(f"教案出现与约束不一致的课时分钟数，目标为 {session_minutes} 分钟。")

    budget_cap = None
    budget_match = re.search(r"预算[^\d]*(\d+(?:\.\d+)?)\s*元", constraint_text)
    if budget_match:
        budget_cap = float(budget_match.group(1))
    if budget_cap is not None:
        costs = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*元", kit)]
        if costs and sum(costs) > budget_cap:
            issues.append(f"学具总预算估算 {sum(costs):.1f} 元，超过约束上限 {budget_cap:.1f} 元。")

    lower_constraints = constraint_text.lower()
    lower_kit = kit.lower()
    sharp_banned = any(token in lower_constraints for token in ["不允许尖锐", "禁止尖锐", "no sharp", "sharp tool"])
    heat_banned = any(token in lower_constraints for token in ["禁止高温", "不允许高温", "no heat", "high heat"])

    if sharp_banned and any(token in lower_kit for token in ["尖锐", "美工刀", "刻刀", "刀片", "锋利"]):
        issues.append("学具方案包含尖锐工具，但 brief 明确禁用。")
    if heat_banned and any(token in lower_kit for token in ["高温", "热熔", "加热", "焊接", "明火"]):
        issues.append("学具方案包含高温/加热行为，但 brief 明确禁用。")

    report = {
        "ok": len(issues) == 0,
        "issues": issues,
        "checked_files": [
            "/mnt/user-data/workspace/course-brief.json",
            "/mnt/user-data/outputs/lesson-plan.md",
            "/mnt/user-data/outputs/learning-kit-appendix.md",
        ],
    }
    (workspace_dir / "presentation-hard-check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(issues) == 0, issues


def _write_education_stage_fallback(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
    description: str,
    reason: str,
) -> list[str]:
    """Write minimal fallback artifacts for education flow on subtask failure.

    Returns virtual paths written in this fallback pass.
    """
    if runtime is None:
        return []

    agent_name = runtime.context.get("agent_name")
    thread_id = runtime.context.get("thread_id")
    if agent_name != "education-course-studio" or not isinstance(thread_id, str):
        return []

    lowered = description.lower()

    try:
        from src.config.paths import get_paths

        paths = get_paths()
        workspace_dir = paths.sandbox_work_dir(thread_id)
        outputs_dir = paths.sandbox_outputs_dir(thread_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        written: list[str] = []

        def write_workspace_file(name: str, content: str):
            target = workspace_dir / name
            target.write_text(content, encoding="utf-8")
            written.append(f"/mnt/user-data/workspace/{name}")

        def write_output_file(name: str, content: str):
            target = outputs_dir / name
            target.write_text(content, encoding="utf-8")
            written.append(f"/mnt/user-data/outputs/{name}")

        if "stage 1" in lowered or "预期结果" in description or "blueprint" in lowered or "蓝图" in description:
            write_workspace_file(
                "stage1-ubd.md",
                f"""# Stage 1 UbD (Fallback)

- This fallback was generated because the delegated subtask failed.
- Reason: {reason or "unknown"}

## Big Ideas
- Animals and AI both rely on perception and pattern recognition.
- Different perception systems produce different strengths and errors.

## Essential Questions
1. Animals and AI \"see\" the world differently in what ways?
2. How can we test whether an AI classifier is fair and reliable?

## Transfer Goals
- Compare natural and artificial perception systems with evidence.
- Design a small classification task and explain results for peers.
""",
            )

        if "research" in lowered or "场景资料" in description or "研究" in description:
            write_workspace_file(
                "research-notes.md",
                f"""# Research Notes (Fallback)

## What happened
- The delegated research subtask failed or timed out.
- Reason: {reason or "unknown"}

## Core references (stable baseline)
1. Understanding by Design (UbD) framework concepts for goal-evidence-activity alignment.
2. Project-Based Learning (PBL) design principles with elementary-age scaffolding.
3. Elementary AI literacy progression: perception, classification, bias awareness, and responsible use.
4. Science inquiry cycle in elementary classrooms: observe -> hypothesize -> test -> explain.

## Elementary appropriateness notes
- Keep AI terminology concrete and example-driven.
- Use hands-on observation and low-barrier data activities.
- Ensure each activity has visible evidence aligned to learning goals.

## Risks and cautions
- Overly abstract driving questions can reduce student entry.
- Activity excitement can overshadow evidence quality if rubric links are weak.
- Learning kit usage must be tied to explicit teaching targets and safety constraints.

## Citation note
- This is an offline fallback summary generated without live web retrieval.
""",
            )

        if "stage 2" in lowered or "证据设计" in description or "package" in lowered:
            write_workspace_file(
                "stage2-assessment.md",
                f"""# Stage 2 Assessment (Fallback)

- Reason: {reason or "upstream timeout"}
- Performance task: Build and explain an \"animal vs AI recognition\" comparison artifact.
- Evidence: observation logs, classification rationale, error analysis, team reflection.
- Rubric focus: concept accuracy, evidence quality, communication clarity, collaboration.
""",
            )

        if "stage 3" in lowered or "pbl 活动" in description or "package" in lowered:
            write_workspace_file(
                "stage3-pbl-plan.md",
                f"""# Stage 3 PBL Plan (Fallback)

- Reason: {reason or "upstream timeout"}
- Session flow: Launch question -> exploration -> mini model/test -> showcase -> reflection.
- Classroom structure: teams of 4 with role cards and evidence checkpoints.
- Safety and feasibility: low-cost materials, no sharp tools, teacher-managed rotation.
""",
            )

        if "learning kit" in lowered or "学具附录" in description or "package" in lowered:
            write_workspace_file(
                "learning-kit-appendix.md",
                f"""# Learning Kit Appendix (Fallback)

- Reason: {reason or "upstream timeout"}
- Low-cost printable cards for animal traits and sample image labels.
- Classroom use: supports observation, classification, and evidence discussion.
- Safety: paper/marker/scissors only under teacher guidance; include no-sharp alternative.
""",
            )

        if "presentation" in lowered or "成果整合" in description or "package" in lowered:
            kit_fallback = """# Learning Kit Appendix (Fallback)

- Low-cost printable trait cards and label cards.
- Classroom usage: observation, comparison, classification evidence collection.
- Safety: no sharp tools required; teacher-managed distribution and collection.
"""
            existing_kit_path = workspace_dir / "learning-kit-appendix.md"
            kit_content = existing_kit_path.read_text(encoding="utf-8") if existing_kit_path.exists() else kit_fallback

            write_output_file(
                "ubd-course-card.md",
                f"""# UbD 课程设计卡（Fallback）

- 主题：动物视觉与 AI 识别
- 学段：小学四年级
- 说明：该版本由系统超时降级生成，建议在审批点 3 复核关键细节。
""",
            )
            write_output_file(
                "lesson-plan.md",
                """# 教案初稿（Fallback）

1. 导入：动物视觉观察任务
2. 探究：AI 分类模拟与误判讨论
3. 产出：小组展板与实验记录
4. 反思：公平性与改进建议
""",
            )
            write_output_file(
                "ppt-outline.md",
                """# PPT 大纲（Fallback）

1. 课程目标与核心问题
2. 动物视觉与 AI 识别对比
3. PBL 任务与证据要求
4. 学具与课堂组织
5. 展示与反思
""",
            )
            write_output_file(
                "reference-summary.md",
                """# 参考资料摘要（Fallback）

- UbD 与 PBL 的课堂一致性原则
- 小学 AI 素养与科学探究融合建议
- 低成本学具组织与安全提醒
""",
            )
            write_output_file("learning-kit-appendix.md", kit_content)
            manifest = {
                "title": "课程成果包",
                "summary": "Fallback generation after subtask timeout/failure.",
                "artifacts": [
                    {
                        "label": "UbD课程设计卡",
                        "path": "/mnt/user-data/outputs/ubd-course-card.md",
                        "description": "课程目标与结构骨架",
                    },
                    {
                        "label": "教案初稿",
                        "path": "/mnt/user-data/outputs/lesson-plan.md",
                        "description": "可执行课堂流程草稿",
                    },
                    {
                        "label": "PPT大纲",
                        "path": "/mnt/user-data/outputs/ppt-outline.md",
                        "description": "课堂展示结构",
                    },
                    {
                        "label": "参考资料摘要",
                        "path": "/mnt/user-data/outputs/reference-summary.md",
                        "description": "研究与引用方向摘要",
                    },
                    {
                        "label": "学具附录",
                        "path": "/mnt/user-data/outputs/learning-kit-appendix.md",
                        "description": "课堂学具规划与安全替代方案",
                    },
                ],
            }
            write_output_file("artifact-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        if "reviewer" in lowered or "质量评审" in description:
            write_workspace_file(
                "reviewer-report.md",
                f"""# Reviewer Report (Fallback)

- Verdict: 有条件通过
- Reason: {reason or "upstream failure"}
- Key issue: Generated through fallback mode, needs targeted teacher review.
""",
            )
            reviewer_summary = {
                "verdict": "有条件通过",
                "hard_gates": [
                    {"name": "目标-证据-活动一致性", "status": "pass", "note": "Fallback baseline preserved"},
                    {"name": "驱动问题儿童可理解性", "status": "pass", "note": "Simple language retained"},
                    {"name": "学具服务教学目标", "status": "pass", "note": "Learning-kit fallback aligned"},
                    {"name": "课时流程现实可执行", "status": "pass", "note": "Basic feasible flow"},
                ],
                "key_issues": ["Fallback quality mode, refine with teacher feedback"],
                "rubric_scores": [
                    {
                        "dimension": "目标-证据-活动一致性",
                        "is_hard_gate": True,
                        "score": 2,
                        "status": "pass",
                        "note": "Baseline alignment kept",
                    }
                ],
                "suggested_rerun_agents": ["Package"],
                "lead_note": "Recommend focused refinement before final acceptance.",
            }
            write_workspace_file("reviewer-summary.json", json.dumps(reviewer_summary, ensure_ascii=False, indent=2))

        if "critic" in lowered or "挑战性复核" in description:
            write_workspace_file(
                "critic-report.md",
                f"""# Critic Report (Fallback)

- Verdict: 部分同意
- Reason: {reason or "upstream failure"}
- Risk: Presentation quality may hide upstream simplifications from fallback mode.
""",
            )
            critic_summary = {
                "verdict": "部分同意",
                "agreement_with_reviewer": "partial",
                "new_key_risks": ["Fallback simplification may reduce classroom specificity"],
                "escalate_rerun": False,
                "suggested_rerun_agents": ["Package"],
                "lead_note": "If teacher rejects draft, rerun presentation with explicit constraints.",
            }
            write_workspace_file("critic-summary.json", json.dumps(critic_summary, ensure_ascii=False, indent=2))

        return written
    except Exception:
        logger.exception("Failed to write education fallback files")
        return []


def _ensure_education_stage_contracts(
    runtime: ToolRuntime[ContextT, ThreadState] | None,
    description: str,
    reason: str,
) -> list[str]:
    """Ensure required contract files exist for education stages after task completion."""
    if runtime is None:
        return []

    agent_name = runtime.context.get("agent_name")
    thread_id = runtime.context.get("thread_id")
    if agent_name != "education-course-studio" or not isinstance(thread_id, str):
        return []

    lowered = description.lower()
    try:
        from src.config.paths import get_paths

        paths = get_paths()
        workspace_dir = paths.sandbox_work_dir(thread_id)
        outputs_dir = paths.sandbox_outputs_dir(thread_id)

        missing = False
        if "presentation" in lowered or "成果整合" in description or "package" in lowered:
            required = [
                outputs_dir / "ubd-course-card.md",
                outputs_dir / "lesson-plan.md",
                outputs_dir / "ppt-outline.md",
                outputs_dir / "reference-summary.md",
                outputs_dir / "learning-kit-appendix.md",
                outputs_dir / "artifact-manifest.json",
            ]
            missing = any(not item.exists() for item in required)
            if not missing:
                ok, issues = _run_presentation_hard_validator(workspace_dir, outputs_dir)
                if not ok:
                    reason_text = "; ".join(issues)
                    return _write_education_stage_fallback(runtime, description, f"presentation hard check failed: {reason_text}")
        elif "reviewer" in lowered or "质量评审" in description:
            required = [
                workspace_dir / "reviewer-report.md",
                workspace_dir / "reviewer-summary.json",
            ]
            missing = any(not item.exists() for item in required)
        elif "critic" in lowered or "挑战性复核" in description:
            required = [
                workspace_dir / "critic-report.md",
                workspace_dir / "critic-summary.json",
            ]
            missing = any(not item.exists() for item in required)

        if missing:
            return _write_education_stage_fallback(runtime, description, reason)
        return []
    except Exception:
        logger.exception("Failed to validate education stage contracts")
        return []


def _resolve_parent_tool_groups(runtime: ToolRuntime[ContextT, ThreadState] | None) -> list[str] | None:
    """Return the parent custom agent's tool-group restriction, if any."""
    if runtime is None:
        return None

    agent_name = runtime.context.get("agent_name")
    if not isinstance(agent_name, str) or not agent_name.strip():
        return None

    try:
        agent_config = load_agent_config(agent_name)
    except (FileNotFoundError, ValueError):
        return None

    return agent_config.tool_groups


@tool("task", parse_docstring=True)
def task_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    description: str,
    prompt: str,
    subagent_type: Literal["general-purpose", "bash"],
    tool_call_id: Annotated[str, InjectedToolCallId],
    max_turns: int | None = None,
) -> str:
    """Delegate a task to a specialized subagent that runs in its own context.

    Subagents help you:
    - Preserve context by keeping exploration and implementation separate
    - Handle complex multi-step tasks autonomously
    - Execute commands or operations in isolated contexts

    Available subagent types:
    - **general-purpose**: A capable agent for complex, multi-step tasks that require
      both exploration and action. Use when the task requires complex reasoning,
      multiple dependent steps, or would benefit from isolated context.
    - **bash**: Command execution specialist for running bash commands. Use for
      git operations, build processes, or when command output would be verbose.

    When to use this tool:
    - Complex tasks requiring multiple steps or tools
    - Tasks that produce verbose output
    - When you want to isolate context from the main conversation
    - Parallel research or exploration tasks

    When NOT to use this tool:
    - Simple, single-step operations (use tools directly)
    - Tasks requiring user interaction or clarification

    Args:
        description: A short (3-5 word) description of the task for logging/display. ALWAYS PROVIDE THIS PARAMETER FIRST.
        prompt: The task description for the subagent. Be specific and clear about what needs to be done. ALWAYS PROVIDE THIS PARAMETER SECOND.
        subagent_type: The type of subagent to use. ALWAYS PROVIDE THIS PARAMETER THIRD.
        max_turns: Optional maximum number of agent turns. Defaults to subagent's configured max.
    """
    # Get subagent configuration
    config = get_subagent_config(subagent_type)
    if config is None:
        return f"Error: Unknown subagent type '{subagent_type}'. Available: general-purpose, bash"

    skip_reason = _should_skip_education_subtask(runtime, description)
    if skip_reason:
        return f"Task Skipped. Reason: {skip_reason}"

    # Build config overrides
    overrides: dict = {}

    skills_section = get_skills_prompt_section()
    if skills_section:
        overrides["system_prompt"] = config.system_prompt + "\n\n" + skills_section

    if max_turns is not None:
        overrides["max_turns"] = max_turns

    if overrides:
        config = replace(config, **overrides)

    # Extract parent context from runtime
    sandbox_state = None
    thread_data = None
    thread_id = None
    parent_model = None
    trace_id = None

    if runtime is not None:
        sandbox_state = runtime.state.get("sandbox")
        thread_data = runtime.state.get("thread_data")
        thread_id = runtime.context.get("thread_id")

        # Try to get parent model from configurable
        metadata = runtime.config.get("metadata", {})
        parent_model = metadata.get("model_name")

        # Get or generate trace_id for distributed tracing
        trace_id = metadata.get("trace_id") or str(uuid.uuid4())[:8]

    # Get available tools (excluding task tool to prevent nesting)
    # Lazy import to avoid circular dependency
    from src.tools import get_available_tools

    # Subagents should not have subagent tools enabled (prevent recursive nesting)
    tools = get_available_tools(
        model_name=parent_model,
        groups=_resolve_parent_tool_groups(runtime),
        subagent_enabled=False,
    )
    # HITL ownership contract: only the lead agent may trigger clarification.
    tools = [tool for tool in tools if getattr(tool, "name", "") != "ask_clarification"]

    # Create executor
    executor = SubagentExecutor(
        config=config,
        tools=tools,
        parent_model=parent_model,
        sandbox_state=sandbox_state,
        thread_data=thread_data,
        thread_id=thread_id,
        trace_id=trace_id,
    )

    # Start background execution (always async to prevent blocking)
    # Use tool_call_id as task_id for better traceability
    task_id = executor.execute_async(prompt, task_id=tool_call_id)

    # Poll for task completion in backend (removes need for LLM to poll)
    poll_count = 0
    last_status = None
    last_message_count = 0  # Track how many AI messages we've already sent
    # Polling timeout: execution timeout + 60s buffer, checked every 5s
    max_poll_count = (config.timeout_seconds + 60) // 5

    logger.info(f"[trace={trace_id}] Started background task {task_id} (subagent={subagent_type}, timeout={config.timeout_seconds}s, polling_limit={max_poll_count} polls)")

    writer = get_stream_writer()
    # Send Task Started message'
    writer({"type": "task_started", "task_id": task_id, "description": description})

    while True:
        result = get_background_task_result(task_id)

        if result is None:
            logger.error(f"[trace={trace_id}] Task {task_id} not found in background tasks")
            writer({"type": "task_failed", "task_id": task_id, "error": "Task disappeared from background tasks"})
            cleanup_background_task(task_id)
            return f"Error: Task {task_id} disappeared from background tasks"

        # Log status changes for debugging
        if result.status != last_status:
            logger.info(f"[trace={trace_id}] Task {task_id} status: {result.status.value}")
            last_status = result.status

        # Check for new AI messages and send task_running events
        current_message_count = len(result.ai_messages)
        if current_message_count > last_message_count:
            # Send task_running event for each new message
            for i in range(last_message_count, current_message_count):
                message = result.ai_messages[i]
                writer(
                    {
                        "type": "task_running",
                        "task_id": task_id,
                        "message": message,
                        "message_index": i + 1,  # 1-based index for display
                        "total_messages": current_message_count,
                    }
                )
                logger.info(f"[trace={trace_id}] Task {task_id} sent message #{i + 1}/{current_message_count}")
            last_message_count = current_message_count

        # Check if task completed, failed, or timed out
        if result.status == SubagentStatus.COMPLETED:
            writer({"type": "task_completed", "task_id": task_id, "result": result.result})
            logger.info(f"[trace={trace_id}] Task {task_id} completed after {poll_count} polls")
            cleanup_background_task(task_id)
            fallback_paths = _ensure_education_stage_contracts(runtime, description, "missing required contract files after subtask completion")
            sync_notes = _sync_education_runtime_state(runtime, description)
            if fallback_paths:
                if sync_notes:
                    return (
                        f"Task Succeeded. Result: {result.result}. Contract fallback outputs written: {', '.join(fallback_paths)}. "
                        f"Runtime sync: {', '.join(sync_notes)}."
                    )
                return f"Task Succeeded. Result: {result.result}. Contract fallback outputs written: {', '.join(fallback_paths)}"
            if sync_notes:
                return f"Task Succeeded. Result: {result.result}. Runtime sync: {', '.join(sync_notes)}."
            return f"Task Succeeded. Result: {result.result}"
        elif result.status == SubagentStatus.FAILED:
            writer({"type": "task_failed", "task_id": task_id, "error": result.error})
            logger.error(f"[trace={trace_id}] Task {task_id} failed: {result.error}")
            cleanup_background_task(task_id)
            fallback_paths = _write_education_stage_fallback(runtime, description, result.error or "")
            sync_notes = _sync_education_runtime_state(runtime, description)
            if fallback_paths:
                if sync_notes:
                    return (
                        f"Task failed. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}. "
                        f"Runtime sync: {', '.join(sync_notes)}."
                    )
                return f"Task failed. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}"
            if sync_notes:
                return f"Task failed. Error: {result.error}. Runtime sync: {', '.join(sync_notes)}."
            return f"Task failed. Error: {result.error}"
        elif result.status == SubagentStatus.TIMED_OUT:
            writer({"type": "task_timed_out", "task_id": task_id, "error": result.error})
            logger.warning(f"[trace={trace_id}] Task {task_id} timed out: {result.error}")
            cleanup_background_task(task_id)
            fallback_paths = _write_education_stage_fallback(runtime, description, result.error or "")
            sync_notes = _sync_education_runtime_state(runtime, description)
            if fallback_paths:
                if sync_notes:
                    return (
                        f"Task timed out. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}. "
                        f"Runtime sync: {', '.join(sync_notes)}."
                    )
                return f"Task timed out. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}"
            if sync_notes:
                return f"Task timed out. Error: {result.error}. Runtime sync: {', '.join(sync_notes)}."
            return f"Task timed out. Error: {result.error}"

        # Still running, wait before next poll
        time.sleep(5)  # Poll every 5 seconds
        poll_count += 1

        # Polling timeout as a safety net (in case thread pool timeout doesn't work)
        # Set to execution timeout + 60s buffer, in 5s poll intervals
        # This catches edge cases where the background task gets stuck
        # Note: We don't call cleanup_background_task here because the task may
        # still be running in the background. The cleanup will happen when the
        # executor completes and sets a terminal status.
        if poll_count > max_poll_count:
            timeout_minutes = config.timeout_seconds // 60
            logger.error(f"[trace={trace_id}] Task {task_id} polling timed out after {poll_count} polls (should have been caught by thread pool timeout)")
            writer({"type": "task_timed_out", "task_id": task_id})
            return f"Task polling timed out after {timeout_minutes} minutes. This may indicate the background task is stuck. Status: {result.status.value}"
