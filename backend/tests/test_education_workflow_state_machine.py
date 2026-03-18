"""Deterministic state-machine tests for education checkpoint flow."""

from src.education.schemas import CheckpointDecision, CriticSummaryV2, EducationRunState
from src.education.workflow import apply_checkpoint_decision, normalize_checkpoint_option


def _build_run() -> EducationRunState:
    return EducationRunState(
        id="run_state_machine",
        org_id="org_demo",
        project_id="proj_demo",
        title="状态机测试",
    )


def test_checkpoint2_adjust_research_focus_maps_to_partial_rerun_chain():
    run = _build_run()
    result = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp2-goal-lock",
            option="调整研究重点",
            actor_user_id="teacher-1",
        ),
    )
    assert result.normalized_option == "调整研究重点"
    assert result.reopened_to_cp1 is False
    assert result.rerun_targets == [
        "Research",
        "Learning-Kit",
        "Presentation",
        "Reviewer",
        "Critic",
    ]
    assert result.run.status == "rework"
    assert result.retry_target == "Research"


def test_checkpoint3_alias_option_is_normalized():
    assert normalize_checkpoint_option("仅调整学具附录") == "重做学具附录"
    assert normalize_checkpoint_option("重做最终整合") == "重做最终整理"


def test_checkpoint3_guardrail_reopens_checkpoint1_after_second_rejection():
    run = _build_run()

    first = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher-1",
        ),
    )
    assert first.reopened_to_cp1 is False
    assert first.run.status == "rework"
    assert first.run.guard.draft_review_rework_count == 1
    assert first.rerun_targets == [
        "UbD Stage 3",
        "Learning-Kit",
        "Presentation",
        "Reviewer",
        "Critic",
    ]

    second = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher-1",
        ),
    )
    assert second.reopened_to_cp1 is True
    assert second.run.status == "awaiting_checkpoint"
    assert second.run.current_stage == "Checkpoint 1 Reconfirmation"
    assert second.run.guard.draft_review_rework_count == 0
    assert second.details is not None and "连续两次未接受" in second.details


def test_conflict_from_critic_sets_conservative_recommended_option():
    run = _build_run()
    run.critic_summary = CriticSummaryV2(
        verdict="不同意",
        agreement_with_reviewer="conflict",
        new_key_risks=["目标-评价对齐风险"],
        escalate_rerun=True,
        suggested_rerun_agents=["UbD Stage 1"],
        lead_note="建议保守回退。",
    )
    result = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp2-goal-lock",
            option="继续生成评价与活动",
            actor_user_id="reviewer-1",
        ),
    )
    assert result.recommended_option == "重做课程目标"
