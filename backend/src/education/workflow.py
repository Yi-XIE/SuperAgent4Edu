"""Deterministic education workflow state transitions."""

from dataclasses import dataclass
from typing import Any

from .schemas import CheckpointDecision, CheckpointDecisionResult, CheckpointHistoryItem, EducationRunState
from .workflow_template import (
    checkpoint_enabled,
    enabled_rerun_stages,
    guard_max_local_rework,
    resolve_rerun_map_override,
)

CP2_OPTION_MAP: dict[str, list[str]] = {
    "继续生成评价与活动": [],
    "调整学习目标": ["Blueprint", "Package", "Reviewer", "Critic"],
    "调整项目方向": ["Blueprint", "Package", "Reviewer", "Critic"],
    "调整研究重点": ["Blueprint", "Package", "Reviewer", "Critic"],
}

CP3_OPTION_MAP: dict[str, list[str]] = {
    "接受": [],
    "重做课程目标": ["Blueprint", "Package", "Reviewer", "Critic"],
    "重做评价设计": ["Package", "Reviewer", "Critic"],
    "重做活动流程": ["Package", "Reviewer", "Critic"],
    "重做学具附录": ["Package", "Reviewer", "Critic"],
    "重做最终整理": ["Package", "Reviewer", "Critic"],
}

CP4_OPTION_MAP: dict[str, list[str]] = {
    "一键入库": [],
    "跳过本轮": [],
    "调整分类后入库": [],
}

OPTION_ALIASES = {
    "接受当前草案": "接受",
    "仅调整课程目标与评价": "重做评价设计",
    "仅调整学习活动": "重做活动流程",
    "仅调整学具附录": "重做学具附录",
    "重做最终整合": "重做最终整理",
}

CONSERVATIVE_PRIORITY = [
    "重做课程目标",
    "重做评价设计",
    "重做活动流程",
    "重做学具附录",
    "重做最终整理",
]


def normalize_checkpoint_option(option: str) -> str:
    value = option.strip()
    return OPTION_ALIASES.get(value, value)


@dataclass
class WorkflowContext:
    reviewer_conflict: bool
    critic_escalate: bool


def _with_optional_critic(run: EducationRunState, targets: list[str]) -> list[str]:
    if run.critic_enabled:
        return targets
    return [target for target in targets if target != "Critic"]


def _apply_template_rerun_overrides(
    *,
    run: EducationRunState,
    checkpoint_id: str,
    normalized_option: str,
    default_targets: list[str],
    template_content: dict[str, Any] | None,
) -> list[str]:
    override_map = resolve_rerun_map_override(template_content, checkpoint_id)
    if normalized_option in override_map:
        targets = override_map[normalized_option]
    else:
        targets = default_targets

    targets = _with_optional_critic(run, targets)

    enabled_stages = enabled_rerun_stages(template_content)
    if enabled_stages:
        filtered = [target for target in targets if target in enabled_stages]
        if filtered:
            return filtered
    return targets


def _recommended_option_for_conflict(ctx: WorkflowContext) -> str | None:
    if not (ctx.reviewer_conflict or ctx.critic_escalate):
        return None
    return CONSERVATIVE_PRIORITY[0]


def apply_checkpoint_decision(
    run: EducationRunState,
    decision: CheckpointDecision,
    *,
    template_content: dict[str, Any] | None = None,
) -> CheckpointDecisionResult:
    normalized = normalize_checkpoint_option(decision.option)
    rerun_targets: list[str] = []
    reopened_to_cp1 = False
    details: str | None = None
    retry_target: str | None = None
    run.guard.max_local_rework = guard_max_local_rework(
        template_content,
        max(0, run.guard.max_local_rework),
    )

    if decision.checkpoint_id == "cp1-task-confirmation":
        run.status = "running"
        run.current_stage = "Blueprint"
        run.blueprint_status = "running"
        run.package_status = "pending"
        run.asset_extraction_status = "pending"
    elif decision.checkpoint_id == "cp2-goal-lock":
        rerun_targets = _apply_template_rerun_overrides(
            run=run,
            checkpoint_id=decision.checkpoint_id,
            normalized_option=normalized,
            default_targets=CP2_OPTION_MAP.get(normalized, []),
            template_content=template_content,
        )
        if rerun_targets:
            run.status = "rework"
            run.blueprint_status = "running"
            run.package_status = "pending"
            run.current_stage = "Blueprint Rework"
        else:
            run.status = "running"
            run.blueprint_status = "completed"
            run.package_status = "running"
            run.current_stage = "Package"
    elif decision.checkpoint_id == "cp3-draft-review":
        if normalized == "接受":
            run.blueprint_status = "completed"
            run.package_status = "completed"
            run.guard.draft_review_rework_count = 0
            if checkpoint_enabled(
                template_content,
                "cp4-asset-extraction-confirm",
                default=True,
            ):
                run.status = "awaiting_checkpoint"
                run.current_stage = "Checkpoint 4 Asset Extraction"
                run.asset_extraction_status = "ready_for_confirmation"
            else:
                run.status = "accepted"
                run.current_stage = "Accepted"
                run.asset_extraction_status = "skipped"
        else:
            # Guardrail: allow one local rework; second rejection reopens checkpoint 1.
            if run.guard.draft_review_rework_count >= run.guard.max_local_rework:
                reopened_to_cp1 = True
                run.status = "awaiting_checkpoint"
                run.current_stage = "Checkpoint 1 Reconfirmation"
                details = (
                    f"已连续 {run.guard.max_local_rework + 1} 次未接受，"
                    "系统触发任务约束重开确认。"
                )
                run.guard.draft_review_rework_count = 0
                run.blueprint_status = "pending"
                run.package_status = "pending"
                run.asset_extraction_status = "pending"
            else:
                run.guard.draft_review_rework_count += 1
                rerun_targets = _apply_template_rerun_overrides(
                    run=run,
                    checkpoint_id=decision.checkpoint_id,
                    normalized_option=normalized,
                    default_targets=CP3_OPTION_MAP.get(normalized, []),
                    template_content=template_content,
                )
                run.status = "rework"
                if "Blueprint" in rerun_targets:
                    run.blueprint_status = "running"
                    run.package_status = "pending"
                    run.current_stage = "Blueprint Rework"
                elif "Package" in rerun_targets:
                    run.package_status = "running"
                    run.current_stage = "Package Rework"
                else:
                    run.current_stage = "Rework"
    elif decision.checkpoint_id == "cp4-asset-extraction-confirm":
        _ = CP4_OPTION_MAP.get(normalized, [])
        run.guard.draft_review_rework_count = 0
        if normalized == "跳过本轮":
            run.asset_extraction_status = "skipped"
            run.current_stage = "Asset Extraction Skipped"
        else:
            run.asset_extraction_status = "confirmed"
            run.current_stage = "Asset Extraction Confirmed"
        run.status = "accepted"
    else:
        run.status = "running"

    if rerun_targets:
        retry_target = rerun_targets[0]
        run.rerun_targets = rerun_targets
    else:
        run.rerun_targets = []

    history = CheckpointHistoryItem(
        checkpoint_id=decision.checkpoint_id,
        raw_option=decision.option,
        normalized_option=normalized,
        actor_user_id=decision.actor_user_id or "unknown",
        rerun_targets=rerun_targets,
        reopened_to_cp1=reopened_to_cp1,
    )
    run.checkpoint_history.append(history)

    ctx = WorkflowContext(
        reviewer_conflict=(
            run.critic_enabled
            and
            run.critic_summary is not None
            and run.critic_summary.agreement_with_reviewer == "conflict"
        ),
        critic_escalate=bool(run.critic_enabled and run.critic_summary and run.critic_summary.escalate_rerun),
    )
    recommended = _recommended_option_for_conflict(ctx)

    run.recommended_option = recommended
    run.retry_target = retry_target
    run.details = details

    return CheckpointDecisionResult(
        run=run,
        normalized_option=normalized,
        rerun_targets=rerun_targets,
        reopened_to_cp1=reopened_to_cp1,
        recommended_option=recommended,
        retry_target=retry_target,
        details=details,
    )
