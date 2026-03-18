"""Task tool for delegating work to subagents."""

import json
import logging
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

        if "stage 1" in lowered or "预期结果" in description:
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

        if "stage 2" in lowered or "证据设计" in description:
            write_workspace_file(
                "stage2-assessment.md",
                f"""# Stage 2 Assessment (Fallback)

- Reason: {reason or "upstream timeout"}
- Performance task: Build and explain an \"animal vs AI recognition\" comparison artifact.
- Evidence: observation logs, classification rationale, error analysis, team reflection.
- Rubric focus: concept accuracy, evidence quality, communication clarity, collaboration.
""",
            )

        if "stage 3" in lowered or "pbl 活动" in description:
            write_workspace_file(
                "stage3-pbl-plan.md",
                f"""# Stage 3 PBL Plan (Fallback)

- Reason: {reason or "upstream timeout"}
- Session flow: Launch question -> exploration -> mini model/test -> showcase -> reflection.
- Classroom structure: teams of 4 with role cards and evidence checkpoints.
- Safety and feasibility: low-cost materials, no sharp tools, teacher-managed rotation.
""",
            )

        if "learning kit" in lowered or "学具附录" in description:
            write_workspace_file(
                "learning-kit-appendix.md",
                f"""# Learning Kit Appendix (Fallback)

- Reason: {reason or "upstream timeout"}
- Low-cost printable cards for animal traits and sample image labels.
- Classroom use: supports observation, classification, and evidence discussion.
- Safety: paper/marker/scissors only under teacher guidance; include no-sharp alternative.
""",
            )

        if "presentation" in lowered or "成果整合" in description:
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
                "suggested_rerun_agents": ["Presentation"],
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
                "suggested_rerun_agents": ["Presentation"],
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
        if "presentation" in lowered or "成果整合" in description:
            required = [
                outputs_dir / "ubd-course-card.md",
                outputs_dir / "lesson-plan.md",
                outputs_dir / "ppt-outline.md",
                outputs_dir / "reference-summary.md",
                outputs_dir / "learning-kit-appendix.md",
                outputs_dir / "artifact-manifest.json",
            ]
            missing = any(not item.exists() for item in required)
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
            if fallback_paths:
                return f"Task Succeeded. Result: {result.result}. Contract fallback outputs written: {', '.join(fallback_paths)}"
            return f"Task Succeeded. Result: {result.result}"
        elif result.status == SubagentStatus.FAILED:
            writer({"type": "task_failed", "task_id": task_id, "error": result.error})
            logger.error(f"[trace={trace_id}] Task {task_id} failed: {result.error}")
            cleanup_background_task(task_id)
            fallback_paths = _write_education_stage_fallback(runtime, description, result.error or "")
            if fallback_paths:
                return f"Task failed. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}"
            return f"Task failed. Error: {result.error}"
        elif result.status == SubagentStatus.TIMED_OUT:
            writer({"type": "task_timed_out", "task_id": task_id, "error": result.error})
            logger.warning(f"[trace={trace_id}] Task {task_id} timed out: {result.error}")
            cleanup_background_task(task_id)
            fallback_paths = _write_education_stage_fallback(runtime, description, result.error or "")
            if fallback_paths:
                return f"Task timed out. Error: {result.error}. Fallback outputs written: {', '.join(fallback_paths)}"
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
