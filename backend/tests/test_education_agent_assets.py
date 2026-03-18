"""Smoke and contract tests for education-course-studio assets."""

import os
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

from src.config.agents_config import load_agent_config, load_agent_soul
from src.config.paths import Paths


def _repo_root() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root


def _repo_source_paths() -> Paths:
    return Paths(base_dir=_repo_root())


def _load_source_soul() -> str:
    with patch("src.config.agents_config.get_paths", return_value=_repo_source_paths()):
        soul = load_agent_soul("education-course-studio")
    assert soul is not None
    return soul


def test_education_agent_config_loads_from_source_assets():
    with patch("src.config.agents_config.get_paths", return_value=_repo_source_paths()):
        config = load_agent_config("education-course-studio")

    assert config.name == "education-course-studio"
    assert config.tool_groups == ["web", "file:read", "file:write"]
    assert "Elementary AI & science course studio" in config.description


def test_education_agent_soul_loads_from_source_assets():
    soul = _load_source_soul()
    assert "Fixed Workflow" in soul
    assert "course-brief.json" in soul


def test_sync_script_validates_and_syncs_assets(tmp_path):
    repo_root = _repo_root()
    script_path = repo_root / "scripts" / "sync-education-assets.sh"
    deer_flow_home = tmp_path / ".deer-flow"

    env = os.environ.copy()
    env["DEER_FLOW_HOME"] = str(deer_flow_home)

    first = subprocess.run(
        [str(script_path)],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [str(script_path)],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert (deer_flow_home / "agents" / "education-course-studio" / "config.yaml").exists()
    assert (deer_flow_home / "agents" / "education-course-studio" / "SOUL.md").exists()


def test_soul_contains_checkpoint_contract_for_frontend_cards():
    soul = _load_source_soul()

    required_contexts = [
        "任务确认点：请确认本轮课程设计约束",
        "课程目标锁定点：请确认 UbD 目标与项目方向",
        "草案评审点：请确认最终课程包",
    ]
    for context in required_contexts:
        assert context in soul

    required_options = [
        "继续并锁定当前任务约束",
        "补充课时与学具限制",
        "重新聚焦课程主题",
        "继续生成评价与活动",
        "调整学习目标",
        "调整项目方向",
        "调整研究重点",
        "接受",
        "重做课程目标",
        "重做评价设计",
        "重做活动流程",
        "重做学具附录",
        "重做最终整理",
        "仅调整课程目标与评价",
        "仅调整学习活动",
        "仅调整学具附录",
        "重做最终整合",
    ]
    for option in required_options:
        assert option in soul


def test_soul_contains_required_file_contracts():
    soul = _load_source_soul()

    required_workspace_files = [
        "/mnt/user-data/workspace/course-brief.json",
        "/mnt/user-data/workspace/stage1-ubd.md",
        "/mnt/user-data/workspace/research-notes.md",
        "/mnt/user-data/workspace/stage2-assessment.md",
        "/mnt/user-data/workspace/stage3-pbl-plan.md",
        "/mnt/user-data/workspace/learning-kit-appendix.md",
    ]
    required_workspace_output_names = [
        "reviewer-report.md",
        "reviewer-summary.json",
        "critic-report.md",
        "critic-summary.json",
        "draft-review-guard.json",
    ]
    required_output_files = [
        "ubd-course-card.md",
        "lesson-plan.md",
        "ppt-outline.md",
        "learning-kit-appendix.md",
        "reference-summary.md",
        "artifact-manifest.json",
    ]

    for file_path in required_workspace_files:
        assert file_path in soul

    assert "/mnt/user-data/workspace" in soul
    for file_name in required_workspace_output_names:
        assert file_name in soul

    assert "/mnt/user-data/outputs" in soul
    for file_name in required_output_files:
        assert file_name in soul


def test_soul_contains_checkpoint_rework_rules():
    soul = _load_source_soul()

    assert "If checkpoint 2 says `调整学习目标`" in soul
    assert "If checkpoint 2 says `调整项目方向`" in soul
    assert "If checkpoint 2 says `调整研究重点`" in soul
    assert "If checkpoint 3 says `重做学具附录`" in soul
    assert "If checkpoint 3 says `重做最终整理`" in soul
    assert "- `Critic`" in soul
    assert "Draft review guardrail:" in soul
    assert "do NOT continue local reruns" in soul
    assert "Legacy option aliases must remain valid" in soul
    assert "- `Reviewer`" in soul


def test_soul_contains_reviewer_stage_contract():
    soul = _load_source_soul()

    assert "### Stage 6. Reviewer" in soul
    assert "### Stage 7. Critic" in soul
    assert "[Reviewer] 课程质量评审" in soul
    assert "[Critic] 挑战性复核" in soul
    assert "reviewer-summary.json" in soul
    assert "critic-summary.json" in soul
    assert "agreement_with_reviewer" in soul
    assert "rubric_scores" in soul


def test_all_required_education_skills_exist():
    repo_root = _repo_root()
    required_skills = [
        "education-intake",
        "ubd-stage-1",
        "education-research",
        "ubd-stage-2",
        "ubd-stage-3-pbl",
        "learning-kit-planning",
        "education-presentation",
        "course-quality-review",
        "course-quality-critic",
    ]
    for skill_name in required_skills:
        skill_file = repo_root / "skills" / "custom" / skill_name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill contract: {skill_file}"


def test_checkpoint_context_headings_follow_expected_pattern():
    soul = _load_source_soul()

    headings = re.findall(r"`context`:\s*`([^`]+)`", soul)
    assert "任务确认点：请确认本轮课程设计约束" in headings
    assert "课程目标锁定点：请确认 UbD 目标与项目方向" in headings
    assert "草案评审点：请确认最终课程包" in headings
