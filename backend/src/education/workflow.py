"""Deterministic education workflow state transitions."""

from dataclasses import dataclass

from .schemas import CheckpointDecision, CheckpointDecisionResult, CheckpointHistoryItem, EducationRunState

CP2_OPTION_MAP: dict[str, list[str]] = {
    "继续生成评价与活动": [],
    "调整学习目标": ["UbD Stage 1", "Research", "UbD Stage 2", "UbD Stage 3", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "调整项目方向": ["Research", "UbD Stage 3", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "调整研究重点": ["Research", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
}

CP3_OPTION_MAP: dict[str, list[str]] = {
    "接受": [],
    "重做课程目标": ["UbD Stage 1", "Research", "UbD Stage 2", "UbD Stage 3", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "重做评价设计": ["UbD Stage 2", "UbD Stage 3", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "重做活动流程": ["UbD Stage 3", "Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "重做学具附录": ["Learning-Kit", "Presentation", "Reviewer", "Critic"],
    "重做最终整理": ["Presentation", "Reviewer", "Critic"],
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


def _recommended_option_for_conflict(ctx: WorkflowContext) -> str | None:
    if not (ctx.reviewer_conflict or ctx.critic_escalate):
        return None
    return CONSERVATIVE_PRIORITY[0]


def apply_checkpoint_decision(
    run: EducationRunState,
    decision: CheckpointDecision,
) -> CheckpointDecisionResult:
    normalized = normalize_checkpoint_option(decision.option)
    rerun_targets: list[str] = []
    reopened_to_cp1 = False
    details: str | None = None
    retry_target: str | None = None

    if decision.checkpoint_id == "cp2-goal-lock":
        rerun_targets = CP2_OPTION_MAP.get(normalized, [])
        run.status = "rework" if rerun_targets else "running"
    elif decision.checkpoint_id == "cp3-draft-review":
        if normalized == "接受":
            run.status = "accepted"
            run.current_stage = "Completed"
            run.guard.draft_review_rework_count = 0
        else:
            # Guardrail: allow one local rework; second rejection reopens checkpoint 1.
            if run.guard.draft_review_rework_count >= run.guard.max_local_rework:
                reopened_to_cp1 = True
                run.status = "awaiting_checkpoint"
                run.current_stage = "Checkpoint 1 Reconfirmation"
                details = "已连续两次未接受，系统触发任务约束重开确认。"
                run.guard.draft_review_rework_count = 0
            else:
                run.guard.draft_review_rework_count += 1
                rerun_targets = CP3_OPTION_MAP.get(normalized, [])
                run.status = "rework"
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
            run.critic_summary is not None
            and run.critic_summary.agreement_with_reviewer == "conflict"
        ),
        critic_escalate=bool(run.critic_summary and run.critic_summary.escalate_rerun),
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
