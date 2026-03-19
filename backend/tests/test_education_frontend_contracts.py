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
    assert "CHECKPOINT_ID_BY_TYPE" in content
    assert "checkpoint_id" in content
    assert "checkpoint_type" in content
    assert "summary" in content
    assert "recommended_option" in content
    assert "retry_target" in content
    assert "details" in content


def test_frontend_has_task_brief_and_generation_mode_parsers():
    content = _frontend_file("utils.ts").read_text(encoding="utf-8")
    assert "parseEducationTaskBriefCard" in content
    assert "parseEducationGenerationModeCard" in content
    assert "buildEducationStarterPrompt" in content
    assert "任务简报卡" in content
    assert "生成策略确认卡" in content


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


def test_frontend_has_education_hub_route_and_sections():
    content = _workspace_page("education/page.tsx").read_text(encoding="utf-8")
    assert "EducationHubPage" in content
    assert "知识花园" in content
    assert "统一查看课包、素材、资源库和教学反馈" in content
    assert "TabsTrigger value=\"packages\"" in content
    assert "TabsTrigger value=\"assets\"" in content
    assert "TabsTrigger value=\"resources\"" in content
    assert "TabsTrigger value=\"feedback\"" in content
    assert "/workspace/education/resources" in content
    assert "/workspace/education/students" in content


def test_frontend_has_canonical_run_workbench_route():
    content = _workspace_page("education/runs/[run_id]/page.tsx").read_text(
        encoding="utf-8",
    )
    assert "EducationRunWorkbenchShell" in content


def test_frontend_has_run_workbench_components():
    content = _workspace_component_file(
        "education/education-run-workbench-shell.tsx",
    ).read_text(encoding="utf-8")
    assert "EducationStarterPanel" in content
    assert "EducationStageRail" in content
    assert "EducationResultPanel" in content
    assert "buildEducationStarterPrompt" in content
    assert "forceEducationStudio" in content
    assert "disableEducationInfoCards" in content
    assert "findLatestEducationCards" in content
    assert "handleCardApply" in content


def test_frontend_sidebar_has_education_entry():
    content = _workspace_component_file("workspace-nav-chat-list.tsx").read_text(
        encoding="utf-8",
    )
    assert 'href="/workspace/education"' in content
    assert 'href="/workspace/education/templates"' in content
    assert "知识花园" in content
    assert "智能体和工作流" in content


def test_frontend_can_render_checkpoint_card_from_plain_ai_text_fallback():
    content = _messages_core_file("utils.ts").read_text(encoding="utf-8")
    assert "parseEducationCheckpoint" in content
    assert "assistant:clarification" in content


def test_frontend_types_include_run_and_asset_extensions():
    content = _frontend_file("types.ts").read_text(encoding="utf-8")
    assert "thread_id" in content
    assert "bootstrap_status" in content
    assert "bootstrap_at" in content
    assert "generation_mode" in content
    assert "critic_enabled" in content
    assert "critic_policy" in content
    assert "critic_activation_reason" in content
    assert "retrieval_snapshot_at" in content
    assert "asset_extraction_status" in content
    assert "checkpoint_id:" in content
    assert "cp4-asset-extraction-confirm" in content
    assert "export interface TeachingAsset" in content
    assert "export interface AssetExtractionCandidate" in content
    assert "export interface TeachingFeedback" in content
    assert "source: \"manual\" | \"student_review\"" in content


def test_frontend_api_has_student_submit_and_review_mutations():
    content = _frontend_file("api.ts").read_text(encoding="utf-8")
    assert "submitStudentTask(" in content
    assert "reviewStudentSubmission(" in content
    assert "/api/student/tasks/${taskId}/submit" in content
    assert "/api/student/submissions/${submissionId}/review" in content


def test_frontend_api_has_run_result_and_object_routes():
    content = _frontend_file("api.ts").read_text(encoding="utf-8")
    assert "listBlueprints(" in content
    assert "listPackages(" in content
    assert "getRunResult(" in content
    assert "bootstrapRun(" in content
    assert "/api/education/blueprints" in content
    assert "/api/education/packages" in content
    assert "/api/education/runs/${runId}/result" in content
    assert "/api/education/runs/${runId}/bootstrap" in content


def test_chat_page_passes_run_id_context_and_bootstrap_call():
    content = _workspace_page(
        "agents/[agent_name]/chats/[thread_id]/page.tsx",
    ).read_text(encoding="utf-8")
    assert "run_id" in content
    assert "bootstrapRun(" in content
    assert "runIdFromQuery" in content
    assert "runIdFromThread" in content
    assert "ensureEducationBootstrap" in content
    assert "/workspace/education/runs/" in content


def test_message_list_supports_force_education_mode_and_card_toggle():
    content = _message_component_file("message-list.tsx").read_text(
        encoding="utf-8",
    )
    assert "forceEducationStudio" in content
    assert "disableEducationInfoCards" in content
    assert "typeof forceEducationStudio === \"boolean\"" in content


def test_frontend_task_brief_card_field_has_key_for_roundtrip_edit():
    content = _frontend_file("types.ts").read_text(encoding="utf-8")
    assert "export interface EducationTaskBriefField" in content
    assert "key: string;" in content
