"""Contract tests for education checkpoint clarification message formatting."""

import re

from src.agents.middlewares.clarification_middleware import ClarificationMiddleware


def _parse_like_frontend(content: str) -> dict | None:
    """Minimal parser equivalent to frontend education checkpoint parsing rules."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return None

    option_lines = [line for line in lines if re.match(r"^\s*\d+\.\s+", line)]
    if not option_lines:
        return None

    body_lines = [line for line in lines if not re.match(r"^\s*\d+\.\s+", line)]
    if not body_lines:
        return None

    heading = re.sub(r"^[^A-Za-z0-9\u4e00-\u9fa5\[]+", "", body_lines[0]).strip()
    match = re.match(r"^(任务确认点|课程目标锁定点|草案评审点)\s*[:：]?\s*(.*)$", heading)
    if not match:
        return None

    options = []
    for line in option_lines:
        opt_match = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if not opt_match:
            continue
        options.append(opt_match.group(2).strip())

    if not options:
        return None

    metadata: dict[str, str] = {}
    for line in body_lines[1:]:
        meta_match = re.match(r"^([a-z_]+)\s*:\s*(.+)$", line)
        if not meta_match:
            continue
        key = meta_match.group(1).lower()
        if key in {"checkpoint_id", "recommended_option", "retry_target", "details"}:
            metadata[key] = meta_match.group(2).strip()

    return {
        "title": match.group(1),
        "context": match.group(2).strip(),
        "options": options,
        **metadata,
    }


def test_all_three_education_checkpoints_are_frontend_parseable():
    middleware = ClarificationMiddleware()

    cases = [
        {
            "question": "请确认课时与学具限制。",
            "clarification_type": "missing_info",
            "context": "任务确认点：请确认本轮课程设计约束",
            "options": [
                "继续并锁定当前任务约束",
                "补充课时与学具限制",
                "重新聚焦课程主题",
            ],
            "expected_title": "任务确认点",
        },
        {
            "question": "是否继续进入评价与活动设计？",
            "clarification_type": "approach_choice",
            "context": "课程目标锁定点：请确认 UbD 目标与项目方向",
            "options": [
                "继续生成评价与活动",
                "调整学习目标",
                "调整项目方向",
                "调整研究重点",
            ],
            "expected_title": "课程目标锁定点",
        },
        {
            "question": "请确认最终课程包是否接受。",
            "clarification_type": "suggestion",
            "context": "草案评审点：请确认最终课程包",
            "options": [
                "接受",
                "重做课程目标",
                "重做评价设计",
                "重做活动流程",
                "重做学具附录",
                "重做最终整理",
            ],
            "expected_title": "草案评审点",
        },
    ]

    for case in cases:
        message = middleware._format_clarification_message(case)
        parsed = _parse_like_frontend(message)
        assert parsed is not None
        assert parsed["title"] == case["expected_title"]
        assert parsed["context"] != ""
        assert parsed["options"] == case["options"]


def test_draft_review_checkpoint_with_reviewer_summary_is_parseable():
    middleware = ClarificationMiddleware()
    message = middleware._format_clarification_message(
        {
            "question": (
                "Reviewer结论：有条件通过。"
                " 关键风险：学具与活动衔接不足。"
                " 建议回退范围：Learning-Kit + Presentation + Reviewer。"
            ),
            "clarification_type": "suggestion",
            "context": "草案评审点：请确认最终课程包",
            "options": [
                "接受",
                "重做课程目标",
                "重做评价设计",
                "重做活动流程",
                "重做学具附录",
                "重做最终整理",
            ],
        }
    )

    parsed = _parse_like_frontend(message)
    assert parsed is not None
    assert parsed["title"] == "草案评审点"
    assert parsed["context"] == "请确认最终课程包"
    assert parsed["options"] == ["接受", "重做课程目标", "重做评价设计", "重做活动流程", "重做学具附录", "重做最终整理"]


def test_draft_review_checkpoint_with_reviewer_critic_conflict_is_parseable():
    middleware = ClarificationMiddleware()
    message = middleware._format_clarification_message(
        {
            "question": (
                "Reviewer结论：有条件通过。Critic结论：不同意。"
                " 冲突摘要：Reviewer认为可局部返工，Critic认为目标-证据链仍断裂。"
                "\ncheckpoint_id: cp3-draft-review\n"
                "recommended_option: 重做评价设计\n"
                "retry_target: UbD Stage 2\n"
                "details: 第二次非接受将触发重开任务约束确认。"
            ),
            "clarification_type": "suggestion",
            "context": "草案评审点：请确认最终课程包",
            "options": [
                "接受",
                "重做课程目标",
                "重做评价设计",
                "重做活动流程",
                "重做学具附录",
                "重做最终整理",
            ],
        }
    )

    parsed = _parse_like_frontend(message)
    assert parsed is not None
    assert parsed["title"] == "草案评审点"
    assert parsed["checkpoint_id"] == "cp3-draft-review"
    assert parsed["retry_target"] == "UbD Stage 2"


def test_checkpoint_with_metadata_lines_keeps_card_parse_contract():
    middleware = ClarificationMiddleware()
    message = middleware._format_clarification_message(
        {
            "question": (
                "请确认是否继续生成。\n"
                "checkpoint_id: cp2-goal-lock\n"
                "recommended_option: 1\n"
                "retry_target: Research\n"
                "details: 若选择调整研究重点，仅回退研究相关链路。"
            ),
            "clarification_type": "approach_choice",
            "context": "课程目标锁定点：请确认 UbD 目标与项目方向",
            "options": [
                "继续生成评价与活动",
                "调整学习目标",
                "调整项目方向",
                "调整研究重点",
            ],
        }
    )

    parsed = _parse_like_frontend(message)
    assert parsed is not None
    assert parsed["title"] == "课程目标锁定点"
    assert parsed["checkpoint_id"] == "cp2-goal-lock"
    assert parsed["recommended_option"] == "1"
    assert parsed["retry_target"] == "Research"


def test_options_stringified_json_array_is_normalized_to_real_options():
    middleware = ClarificationMiddleware()
    message = middleware._format_clarification_message(
        {
            "question": "请选择下一步。",
            "clarification_type": "approach_choice",
            "context": "课程目标锁定点：请确认 UbD 目标与项目方向",
            "options": '["继续生成评价与活动","调整学习目标","调整项目方向"]',
        }
    )

    parsed = _parse_like_frontend(message)
    assert parsed is not None
    assert parsed["options"] == [
        "继续生成评价与活动",
        "调整学习目标",
        "调整项目方向",
    ]


def test_options_plain_string_keeps_single_option_without_char_split():
    middleware = ClarificationMiddleware()
    message = middleware._format_clarification_message(
        {
            "question": "请确认是否继续。",
            "clarification_type": "suggestion",
            "context": "任务确认点：请确认本轮课程设计约束",
            "options": "继续并锁定当前任务约束",
        }
    )

    parsed = _parse_like_frontend(message)
    assert parsed is not None
    assert parsed["options"] == ["继续并锁定当前任务约束"]
