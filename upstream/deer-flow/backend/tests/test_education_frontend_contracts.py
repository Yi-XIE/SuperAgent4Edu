"""Contract checks for education frontend utility behavior."""

from pathlib import Path


def _frontend_file(path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "src" / "core" / "education" / path


def _message_component_file(path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "src" / "components" / "workspace" / "messages" / path


def _workspace_component_file(path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "src" / "components" / "workspace" / path


def _messages_core_file(path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "src" / "core" / "messages" / path


def _workspace_page(path: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "src" / "app" / "workspace" / path


def test_frontend_has_reviewer_summary_types():
    content = _frontend_file("types.ts").read_text(encoding="utf-8")
    assert "export interface ReviewerSummary" in content
    assert "hard_gates" in content
    assert "rubric_scores" in content
    assert "suggested_rerun_agents" in content


def test_frontend_has_critic_summary_types():
    content = _frontend_file("types.ts").read_text(encoding="utf-8")
    assert "export interface CriticSummary" in content
    assert "agreement_with_reviewer" in content
    assert "new_key_risks" in content
    assert "escalate_rerun" in content
    assert "suggested_rerun_agents" in content


def test_frontend_has_reviewer_subtask_stage_mapping():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert 'stage: "Reviewer"' in content
    assert 'label: "质量评审"' in content
    assert "reviewer|课程质量评审|质量评审" in content


def test_frontend_has_critic_subtask_stage_mapping():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert 'stage: "Critic"' in content
    assert 'label: "挑战复核"' in content
    assert "critic|挑战性复核|复核" in content


def test_frontend_reviewer_summary_parser_has_tolerant_fallback():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert "export function parseReviewerSummary" in content
    assert "typeof summary.verdict !== \"string\"" in content
    assert "Array.isArray(summary.rubric_scores)" in content
    assert "parseStringArray(summary.key_issues)" in content
    assert "parseStringArray(summary.suggested_rerun_agents)" in content


def test_frontend_critic_summary_parser_has_tolerant_fallback():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert "export function parseCriticSummary" in content
    assert "typeof summary.agreement_with_reviewer !== \"string\"" in content
    assert "parseStringArray(summary.new_key_risks)" in content
    assert "typeof summary.escalate_rerun === \"boolean\"" in content


def test_frontend_checkpoint_parser_supports_metadata_lines():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert "parseCheckpointMetadata" in content
    assert "checkpoint_id" in content
    assert "checkpoint_type" in content
    assert "summary" in content
    assert "recommended_option" in content
    assert "retry_target" in content
    assert "details" in content


def test_checkpoint_card_renders_recommended_retry_and_reviewer_summary():
    content = _message_component_file("education-checkpoint-card.tsx").read_text(encoding="utf-8")
    assert "parseReviewerSummary" in content
    assert "parseCriticSummary" in content
    assert "recommended_option" in content
    assert "retry_target" in content
    assert "Reviewer 结论" in content
    assert "Critic 复核" in content


def test_frontend_has_education_memory_panel_contract():
    content = _message_component_file("education-memory-panel.tsx").read_text(encoding="utf-8")
    assert "教师记忆区" in content
    assert "本次使用信号" in content
    assert "useMemory(agentName, runId)" in content
    assert "memory.education_signals" in content
    assert "memory.used_signals" in content


def test_frontend_has_education_workbench_route_and_sections():
    content = _workspace_page("education/page.tsx").read_text(encoding="utf-8")
    assert "EducationWorkbenchPage" in content
    assert "教师工作台" in content
    assert "工作流编辑器" in content
    assert "模板市场" in content
    assert "资源库" in content
    assert "学生端" in content


def test_frontend_sidebar_has_education_entry():
    content = _workspace_component_file("workspace-nav-chat-list.tsx").read_text(
        encoding="utf-8",
    )
    assert 'href="/workspace/education"' in content
    assert "t.sidebar.education" in content


def test_frontend_can_render_checkpoint_card_from_plain_ai_text_fallback():
    content = _messages_core_file("utils.ts").read_text(encoding="utf-8")
    assert "parseEducationCheckpoint" in content
    assert "assistant:clarification" in content
