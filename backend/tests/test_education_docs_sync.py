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
    assert "course-quality-critic" in content
    assert "重做学具附录" in content
    assert "重做最终整理" in content
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
        "重做课程目标",
        "重做评价设计",
        "重做活动流程",
        "重做学具附录",
        "重做最终整理",
    ]

    for token in required_tokens:
        assert token in soul
        assert token in docs_combined
