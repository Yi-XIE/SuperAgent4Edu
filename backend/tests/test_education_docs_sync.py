"""Lightweight docs-to-implementation drift checks for education flow."""

from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _find_docs_root() -> Path | None:
    # Support both in-repo docs and parent-workspace docs layout.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "docs" / "plans" / "Hitl-checkpoints.md"
        if candidate.exists():
            return parent / "docs"
    return None


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_soul_contains_reviewer_critic_and_guardrail_contracts():
    soul_path = _repo_root() / "agents" / "education-course-studio" / "SOUL.md"
    content = _read(soul_path)

    assert "### Stage 6. Reviewer" in content
    assert "### Stage 7. Critic" in content
    assert "### Checkpoint 3. Draft Review" in content
    assert "### Checkpoint 4. Asset Extraction Confirm" in content
    assert "course-quality-critic" in content
    assert "重做学具附录" in content
    assert "重做最终整理" in content
    assert "素材提取确认" in content
    assert "draft_review_rework_count" in content


def test_docs_and_soul_share_core_checkpoint_options():
    docs_root = _find_docs_root()
    if docs_root is None:
        pytest.skip("Docs root with HITL checkpoints not found")

    docs_files = [
        docs_root / "plans" / "Hitl-checkpoints.md",
        docs_root / "plans" / "Product-design.md",
        docs_root / "prompts" / "Reviewer-critic-prompts.md",
    ]
    existing_files = [path for path in docs_files if path.exists()]
    if not existing_files:
        pytest.skip("Education docs files not found")

    docs_combined = "\n".join(_read(path) for path in existing_files)
    soul = _read(_repo_root() / "agents" / "education-course-studio" / "SOUL.md")

    required_tokens = [
        "Reviewer",
        "Critic",
        "草案评审点",
        "课程蓝图锁定点",
        "素材提取确认",
        "重做课程目标",
        "重做评价设计",
        "重做活动流程",
        "重做学具附录",
        "重做最终整理",
    ]

    for token in required_tokens:
        assert token in soul
        assert token in docs_combined


def test_docs_cover_gap_closure_runtime_contracts():
    docs_root = _find_docs_root()
    if docs_root is None:
        pytest.skip("Docs root with education plans not found")

    docs_files = [
        docs_root / "plans" / "Implementation-plan.md",
        docs_root / "plans" / "Acceptance-runbook.md",
        docs_root / "plans" / "Product-design.md",
        docs_root / "plans" / "Agent-roles.md",
    ]
    existing_files = [path for path in docs_files if path.exists()]
    if not existing_files:
        pytest.skip("Education docs files not found")

    docs_combined = "\n".join(_read(path) for path in existing_files)
    required_tokens = [
        "workflow_template_id",
        "critic_policy",
        "retrieval_snapshot_at",
        "run_id",
        "thread_id",
        "bootstrap",
        "素材召回",
        "白名单",
        "学生提交",
        "教师评阅",
        "4+1",
        "CP4",
    ]
    for token in required_tokens:
        assert token in docs_combined


def test_docs_cover_behavior_level_acceptance_paths():
    docs_root = _find_docs_root()
    if docs_root is None:
        pytest.skip("Docs root with education plans not found")

    runbook = docs_root / "plans" / "Acceptance-runbook.md"
    implementation = docs_root / "plans" / "Implementation-plan.md"
    if not runbook.exists() or not implementation.exists():
        pytest.skip("Acceptance runbook or implementation plan not found")

    runbook_text = _read(runbook)
    implementation_text = _read(implementation)

    runbook_required = [
        "用例 8：Critic 条件启用",
        "critic_policy=manual_off",
        "critic_policy=auto",
        "workflow_template_id 驱动执行",
        "Checkpoint 4 素材提取确认",
        "学生提交与教师评阅回流",
    ]
    for token in runbook_required:
        assert token in runbook_text

    implementation_required = [
        "Lead -> Blueprint -> Package -> Reviewer",
        "CourseBlueprint",
        "CoursePackage",
        "素材召回",
        "文档和 prompt",
    ]
    for token in implementation_required:
        assert token in implementation_text


def test_runbook_uses_run_thread_unified_terms():
    docs_root = _find_docs_root()
    if docs_root is None:
        pytest.skip("Docs root with education plans not found")

    runbook = docs_root / "plans" / "Acceptance-runbook.md"
    if not runbook.exists():
        pytest.skip("Acceptance runbook not found")

    text = _read(runbook)
    assert "/workspace/education" in text
    assert "Package -> Reviewer -> Critic" in text
    assert "Learning-Kit + Presentation + Reviewer + Critic" not in text


def test_docs_conflict_sections_mark_historical_decisions():
    docs_root = _find_docs_root()
    if docs_root is None:
        pytest.skip("Docs root with education plans not found")

    targets = [
        docs_root / "plans" / "Implementation-plan.md",
        docs_root / "plans" / "Product-design.md",
        docs_root / "plans" / "Acceptance-runbook.md",
        docs_root / "plans" / "Agent-roles.md",
    ]
    existing = [path for path in targets if path.exists()]
    if not existing:
        pytest.skip("Education docs files not found")

    historical_markers = ("历史决策（已失效）", "历史记录（已失效）")
    conflict_words = ("非目标", "暂不处理", "暂不做")
    status_words = ("已完成", "已落代码", "当前实现状态")

    for path in existing:
        text = _read(path)
        if any(word in text for word in conflict_words) and any(word in text for word in status_words):
            assert any(marker in text for marker in historical_markers), (
                f"{path.name} has mixed status/non-goal wording without historical marker"
            )
