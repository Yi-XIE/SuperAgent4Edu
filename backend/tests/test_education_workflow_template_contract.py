"""Template-driven workflow behavior contracts."""

from src.education.schemas import CheckpointDecision, EducationRunState
from src.education.workflow import apply_checkpoint_decision


def _run() -> EducationRunState:
    return EducationRunState(
        id="run_tpl",
        org_id="org_1",
        project_id="proj_1",
        title="模板驱动测试",
        critic_enabled=True,
    )


def test_template_override_changes_cp3_rerun_scope():
    run = _run()
    template_content = {
        "rerun_map": {
            "cp3-draft-review": {
                "重做活动流程": ["Package"],
            }
        }
    }
    result = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    assert result.rerun_targets == ["Package"]
    assert result.run.current_stage == "Package Rework"


def test_template_enabled_stages_can_disable_critic_rerun():
    run = _run()
    template_content = {
        "enabled_stages": ["Blueprint", "Package", "Reviewer"],
    }
    result = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp2-goal-lock",
            option="调整研究重点",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    assert result.rerun_targets == ["Blueprint", "Package", "Reviewer"]
    assert "Critic" not in result.rerun_targets


def test_template_can_disable_cp4_and_accept_directly():
    run = _run()
    template_content = {
        "checkpoints": {
            "cp4-asset-extraction-confirm": False,
        }
    }
    result = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="接受",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    assert result.run.status == "accepted"
    assert result.run.current_stage == "Accepted"
    assert result.run.asset_extraction_status == "skipped"


def test_template_guard_updates_max_local_rework():
    run = _run()
    template_content = {"guard": {"max_local_rework": 2}}
    first = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    second = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    third = apply_checkpoint_decision(
        run,
        CheckpointDecision(
            checkpoint_id="cp3-draft-review",
            option="重做活动流程",
            actor_user_id="teacher_1",
        ),
        template_content=template_content,
    )
    assert first.reopened_to_cp1 is False
    assert second.reopened_to_cp1 is False
    assert third.reopened_to_cp1 is True
