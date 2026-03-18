#!/usr/bin/env python3
"""Run closeout acceptance scenarios for education-course-studio.

This script focuses on reproducible validation for V1.3 closeout:
1. Normal path (CP1 -> CP2 -> CP3 accept)
2. CP2 partial rerun path (adjust research focus)
3. CP3 guardrail path (second rejection reopens CP1)

It writes a single JSON report that includes scenario traces, file-contract checks,
and a lightweight quality summary for the normal path artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.client import DeerFlowClient
from src.config.paths import get_paths
from src.education.schemas import CheckpointDecision, EducationRunState
from src.education.workflow import apply_checkpoint_decision


@dataclass
class ScenarioResult:
    name: str
    thread_id: str
    success: bool
    trace: list[dict[str, Any]]
    checks: dict[str, Any]
    note: str | None = None


def parse_checkpoint(text: str | None) -> str | None:
    if not text:
        return None
    if "任务确认点" in text:
        return "cp1"
    if "课程目标锁定点" in text:
        return "cp2"
    if "草案评审点" in text:
        return "cp3"
    return None


def parse_numbered_options(text: str) -> list[str]:
    options: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.+)$", line.strip())
        if match:
            options.append(match.group(1).strip())
    return options


def build_temp_config(repo_root: Path, subagent_timeout_seconds: int) -> Path:
    source = repo_root / "config.yaml"
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    raw.setdefault("subagents", {})
    raw["subagents"]["timeout_seconds"] = subagent_timeout_seconds
    raw["subagents"].setdefault("agents", {})
    raw["subagents"]["agents"].setdefault("general-purpose", {})
    raw["subagents"]["agents"]["general-purpose"]["timeout_seconds"] = (
        subagent_timeout_seconds
    )
    fd, path = tempfile.mkstemp(prefix="deerflow-closeout-", suffix=".yaml")
    os.close(fd)
    config_path = Path(path)
    config_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def run_turn(
    client: DeerFlowClient,
    *,
    thread_id: str,
    user_message: str,
    model_name: str,
    max_concurrent_subagents: int,
    seen_ids: set[str],
    max_retries: int = 3,
) -> dict[str, Any]:
    latest_clarification: str | None = None
    latest_ai_text: str = ""
    task_descriptions: list[str] = []

    for attempt in range(1, max_retries + 1):
        try:
            for event in client.stream(
                user_message,
                thread_id=thread_id,
                agent_name="education-course-studio",
                model_name=model_name,
                thinking_enabled=False,
                subagent_enabled=True,
                plan_mode=False,
                max_concurrent_subagents=max_concurrent_subagents,
                recursion_limit=120,
            ):
                if event.type != "messages-tuple":
                    continue
                data = event.data
                msg_id = data.get("id")
                if isinstance(msg_id, str):
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)

                msg_type = data.get("type")
                if msg_type == "tool" and data.get("name") == "ask_clarification":
                    latest_clarification = str(data.get("content", ""))
                    continue

                if msg_type == "ai" and data.get("content"):
                    latest_ai_text = str(data["content"])

                if msg_type == "ai" and isinstance(data.get("tool_calls"), list):
                    for call in data["tool_calls"]:
                        if not isinstance(call, dict):
                            continue
                        if call.get("name") != "task":
                            continue
                        args = call.get("args")
                        if isinstance(args, dict):
                            desc = args.get("description")
                            if isinstance(desc, str) and desc.strip():
                                task_descriptions.append(desc.strip())

            # Fallback: some models output checkpoint text in plain AI message.
            if latest_clarification is None and parse_checkpoint(latest_ai_text):
                latest_clarification = latest_ai_text

            if (
                latest_clarification is None
                and not latest_ai_text.strip()
                and not task_descriptions
                and attempt < max_retries
            ):
                # Occasionally a turn returns no message tuple when the provider is
                # under load. Retry this turn instead of treating it as a valid step.
                time.sleep(2)
                continue

            return {
                "clarification": latest_clarification,
                "ai_text": latest_ai_text,
                "task_descriptions": task_descriptions,
            }
        except Exception as exc:  # noqa: BLE001
            text = str(exc)
            is_rate_limited = "Rate limit exceeded" in text
            is_transient = (
                "Connection error" in text
                or "ConnectError" in text
                or "timed out" in text.lower()
            )
            if (
                (is_rate_limited or is_transient)
                and attempt < max_retries
            ):
                time.sleep(65 if is_rate_limited else 5)
                continue
            raise

    raise RuntimeError("Exceeded retry budget in run_turn")


def pick_accept_option(clarification_text: str) -> str:
    options = parse_numbered_options(clarification_text)
    for option in options:
        if "接受" in option and "重做" not in option:
            return option
    return "接受"


def assert_expected_files(thread_id: str) -> dict[str, Any]:
    paths = get_paths()
    outputs = paths.sandbox_outputs_dir(thread_id)
    workspace = paths.sandbox_work_dir(thread_id)
    output_files = [
        "ubd-course-card.md",
        "lesson-plan.md",
        "ppt-outline.md",
        "learning-kit-appendix.md",
        "reference-summary.md",
        "artifact-manifest.json",
    ]
    workspace_files = [
        "course-brief.json",
        "stage1-ubd.md",
        "research-notes.md",
        "stage2-assessment.md",
        "stage3-pbl-plan.md",
        "learning-kit-appendix.md",
        "reviewer-report.md",
        "reviewer-summary.json",
        "critic-report.md",
        "critic-summary.json",
    ]
    return {
        "outputs_dir": str(outputs),
        "workspace_dir": str(workspace),
        "outputs_exists": {name: (outputs / name).exists() for name in output_files},
        "workspace_exists": {
            name: (workspace / name).exists() for name in workspace_files
        },
    }


def extract_quality_summary(thread_id: str) -> dict[str, Any]:
    paths = get_paths()
    workspace = paths.sandbox_work_dir(thread_id)
    outputs = paths.sandbox_outputs_dir(thread_id)

    brief_file = workspace / "course-brief.json"
    kit_file = outputs / "learning-kit-appendix.md"
    lesson_file = outputs / "lesson-plan.md"
    reviewer_file = workspace / "reviewer-summary.json"
    critic_file = workspace / "critic-summary.json"

    summary: dict[str, Any] = {}
    if brief_file.exists():
        brief = json.loads(brief_file.read_text(encoding="utf-8"))
        summary["session_count"] = brief.get("session_count")
        summary["session_length_minutes"] = brief.get("session_length_minutes")
        summary["kit_constraints"] = brief.get("learning_kit", {}).get("constraints", [])
    else:
        summary["session_count"] = None
        summary["session_length_minutes"] = None
        summary["kit_constraints"] = []

    if lesson_file.exists():
        lesson = lesson_file.read_text(encoding="utf-8")
        session_blocks = re.findall(r"^##\s*课时\d+", lesson, flags=re.MULTILINE)
        summary["lesson_session_blocks"] = len(session_blocks)
        session_count = summary.get("session_count")
        summary["session_count_match"] = (
            isinstance(session_count, int) and len(session_blocks) == session_count
        )
    else:
        summary["lesson_session_blocks"] = 0
        summary["session_count_match"] = False

    if kit_file.exists():
        kit_text = kit_file.read_text(encoding="utf-8")
        total_match = re.search(r"合计[^0-9]*([0-9]+(?:\.[0-9]+)?)", kit_text)
        total_cost = float(total_match.group(1)) if total_match else None
        summary["kit_total_cost"] = total_cost

        constraints = summary.get("kit_constraints", [])
        budget_cap = None
        for item in constraints:
            if isinstance(item, str):
                cap_match = re.search(r"([0-9]+)\s*元", item)
                if cap_match:
                    budget_cap = float(cap_match.group(1))
                    break
        summary["budget_cap"] = budget_cap
        if total_cost is not None and budget_cap is not None:
            summary["budget_within_cap"] = total_cost <= budget_cap
        else:
            summary["budget_within_cap"] = None
    else:
        summary["kit_total_cost"] = None
        summary["budget_cap"] = None
        summary["budget_within_cap"] = None

    if reviewer_file.exists():
        reviewer = json.loads(reviewer_file.read_text(encoding="utf-8"))
        summary["reviewer_verdict"] = reviewer.get("verdict")
    else:
        summary["reviewer_verdict"] = None

    if critic_file.exists():
        critic = json.loads(critic_file.read_text(encoding="utf-8"))
        summary["critic_verdict"] = critic.get("verdict")
        summary["critic_agreement"] = critic.get("agreement_with_reviewer")
    else:
        summary["critic_verdict"] = None
        summary["critic_agreement"] = None

    return summary


def scenario_normal_accept(client: DeerFlowClient, model_name: str) -> ScenarioResult:
    thread_id = f"edu-closeout-normal-{uuid.uuid4().hex[:8]}"
    seen_ids: set[str] = set()
    trace: list[dict[str, Any]] = []
    message = (
        "请设计小学5-6年级AI与科学融合课程《动物视觉与机器视觉》，"
        "共4课时，每课时40分钟，采用UbD+PBL。学具预算300元内，"
        "允许打印件，不允许尖锐刀具和高温设备；如约束完整请直接推进到最终交付。"
    )
    fallback_replies = 0
    stale_turns = 0

    for _ in range(12):
        try:
            turn = run_turn(
                client,
                thread_id=thread_id,
                user_message=message,
                model_name=model_name,
                max_concurrent_subagents=1,
                seen_ids=seen_ids,
            )
        except Exception as exc:  # noqa: BLE001
            trace.append(
                {
                    "user_message": message,
                    "checkpoint": None,
                    "task_descriptions": [],
                    "ai_preview": "",
                    "error": str(exc),
                }
            )
            break
        checkpoint = parse_checkpoint(turn["clarification"])
        trace.append(
            {
                "user_message": message,
                "checkpoint": checkpoint,
                "task_descriptions": turn["task_descriptions"],
                "ai_preview": turn["ai_text"][:240],
            }
        )
        if checkpoint == "cp1":
            message = (
                "补充课时与学具限制：小学5-6年级，4课时，每课时40分钟；"
                "预算300元内；允许打印件；不允许尖锐刀具和高温设备。"
            )
            stale_turns = 0
            continue
        if checkpoint == "cp2":
            message = "继续生成评价与活动"
            stale_turns = 0
            continue
        if checkpoint == "cp3":
            clar_text = turn["clarification"] or ""
            message = pick_accept_option(clar_text)
            stale_turns = 0
            continue

        interim = assert_expected_files(thread_id)
        if all(interim["outputs_exists"].values()) and all(
            interim["workspace_exists"].values()
        ):
            break

        # Fallback for models that ask confirmation in plain text instead of
        # emitting formal checkpoint markers/tool calls.
        ai_text = turn.get("ai_text", "")
        if (
            checkpoint is None
            and isinstance(ai_text, str)
            and any(token in ai_text for token in ("请确认", "请提供", "需要确认", "关键信息"))
            and fallback_replies < 3
        ):
            fallback_replies += 1
            message = (
                "继续并锁定当前任务约束。UbD大概念、核心问题、迁移目标与PBL驱动问题请按"
                "小学5-6年级、4课时、预算300元内自动补齐，然后继续下一阶段。"
            )
            stale_turns = 0
            continue

        if turn.get("task_descriptions"):
            message = "继续按既定约束推进，直到生成最终产物并提交草案评审。"
            stale_turns = 0
            continue

        stale_turns += 1
        if stale_turns < 2:
            message = (
                "继续。若你已完成最终整理，请直接输出结果并确保产物文件完整。"
            )
            continue
        break

    checks = assert_expected_files(thread_id)
    quality = extract_quality_summary(thread_id)
    checks["quality_summary"] = quality
    success = all(checks["outputs_exists"].values()) and all(
        checks["workspace_exists"].values()
    )
    return ScenarioResult(
        name="normal_accept",
        thread_id=thread_id,
        success=success,
        trace=trace,
        checks=checks,
    )


def scenario_cp2_adjust_research_state_machine() -> ScenarioResult:
    run = EducationRunState(
        id=f"run-{uuid.uuid4().hex[:8]}",
        org_id="demo-org",
        project_id="demo-project",
        title="state-machine-cp2",
    )
    decision = CheckpointDecision(
        checkpoint_id="cp2-goal-lock",
        option="调整研究重点",
        actor_user_id="tester",
    )
    result = apply_checkpoint_decision(run, decision)
    expected_chain = ["Research", "Learning-Kit", "Presentation", "Reviewer", "Critic"]
    ok = result.rerun_targets == expected_chain
    return ScenarioResult(
        name="cp2_adjust_research_state_machine",
        thread_id=run.id,
        success=ok,
        trace=[
            {
                "checkpoint": decision.checkpoint_id,
                "option": decision.option,
                "rerun_targets": result.rerun_targets,
            }
        ],
        checks={"expected_chain": expected_chain, "actual_chain": result.rerun_targets},
    )


def scenario_cp3_guardrail_state_machine() -> ScenarioResult:
    run = EducationRunState(
        id=f"run-{uuid.uuid4().hex[:8]}",
        org_id="demo-org",
        project_id="demo-project",
        title="state-machine-cp3",
    )
    first = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="tester",
        ),
    )
    second = apply_checkpoint_decision(
        first.run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做学具附录",
            actor_user_id="tester",
        ),
    )
    reopened = (
        second.run.status == "awaiting_checkpoint"
        and second.run.current_stage == "Checkpoint 1 Reconfirmation"
    )
    return ScenarioResult(
        name="cp3_guardrail_state_machine",
        thread_id=run.id,
        success=reopened,
        trace=[
            {
                "first_option": "重做活动流程",
                "first_rerun_targets": first.rerun_targets,
                "first_guard_count": first.run.guard.draft_review_rework_count,
            },
            {
                "second_option": "重做学具附录",
                "second_rerun_targets": second.rerun_targets,
                "second_guard_count": second.run.guard.draft_review_rework_count,
                "status": second.run.status,
                "current_stage": second.run.current_stage,
            },
        ],
        checks={
            "reopened_to_cp1": reopened,
            "status": second.run.status,
            "current_stage": second.run.current_stage,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="step-3.5-flash")
    parser.add_argument("--subagent-timeout", type=int, default=35)
    parser.add_argument(
        "--report",
        default="/tmp/education_closeout_report.json",
        help="Output JSON report path.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config_path = build_temp_config(repo_root, args.subagent_timeout)
    os.environ["DEER_FLOW_CONFIG_PATH"] = str(config_path)

    client = DeerFlowClient(
        model_name=args.model,
        thinking_enabled=False,
        subagent_enabled=True,
        plan_mode=False,
    )

    scenarios = [
        scenario_normal_accept(client, args.model),
        scenario_cp2_adjust_research_state_machine(),
        scenario_cp3_guardrail_state_machine(),
    ]

    payload = {
        "config_path": str(config_path),
        "model": args.model,
        "report_generated_at": int(time.time()),
        "all_success": all(s.success for s in scenarios),
        "scenarios": [
            {
                "name": s.name,
                "thread_id": s.thread_id,
                "success": s.success,
                "note": s.note,
                "trace": s.trace,
                "checks": s.checks,
            }
            for s in scenarios
        ],
    }

    report_path = Path(args.report)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"report": str(report_path), "all_success": payload["all_success"]}))


if __name__ == "__main__":
    main()
