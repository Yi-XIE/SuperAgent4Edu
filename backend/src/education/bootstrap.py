"""Education run bootstrap helpers."""

from __future__ import annotations

from .critic_policy import evaluate_critic_activation
from .retrieval import prepare_pre_run_asset_retrieval
from .schemas import EducationRunState, utc_now_iso
from .workflow_template import get_workflow_template_content, guard_max_local_rework


def bootstrap_run_state(state: dict, run: EducationRunState) -> EducationRunState:
    """Initialize first-turn run context before CP1 card generation."""
    prepare_pre_run_asset_retrieval(state, run)

    template_content = get_workflow_template_content(state, run)
    run.guard.max_local_rework = guard_max_local_rework(
        template_content,
        max(0, run.guard.max_local_rework),
    )

    if run.critic_policy == "manual_on":
        run.critic_enabled = True
        run.critic_activation_reason = "manual_on"
    elif run.critic_policy == "manual_off":
        run.critic_enabled = False
        run.critic_activation_reason = "manual_off"
    elif run.critic_policy == "auto":
        run.critic_enabled, run.critic_activation_reason = evaluate_critic_activation(
            run,
            run.reviewer_summary,
        )

    now = utc_now_iso()
    run.bootstrap_status = "ready"
    run.bootstrap_at = now
    run.updated_at = now
    return run
