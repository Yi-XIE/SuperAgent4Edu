"""Deterministic critic auto-activation policy."""

from __future__ import annotations

from .schemas import EducationRunState, ReviewerSummaryV2

_HIGH_RISK_KEYWORDS = (
    "高风险",
    "安全",
    "禁用",
    "预算",
    "危险",
    "高温",
    "尖锐",
    "risk",
    "safety",
)
_STRICT_REVIEW_KEYWORDS = (
    "严格复核",
    "严格评审",
    "严格审查",
    "challenge",
    "double-check",
    "二次复核",
)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            return True
    return False


def evaluate_critic_activation(
    run: EducationRunState,
    reviewer_summary: ReviewerSummaryV2 | None,
) -> tuple[bool, str]:
    """Return (critic_enabled, activation_reason)."""
    if run.critic_policy != "auto":
        if run.critic_policy == "manual_on":
            return True, "manual_on"
        if run.critic_policy == "manual_off":
            return False, "manual_off"
        return run.critic_enabled, run.critic_activation_reason or "manual"

    reasons: list[str] = []
    signal_text = "\n".join(
        [
            run.title,
            run.details or "",
            "\n".join(run.asset_retrieval_notes),
        ]
    )

    if _contains_any(signal_text, _HIGH_RISK_KEYWORDS):
        reasons.append("high_risk_constraints")
    if _contains_any(signal_text, _STRICT_REVIEW_KEYWORDS):
        reasons.append("teacher_strict_review_preference")

    if reviewer_summary is not None:
        if reviewer_summary.verdict in {"有条件通过", "不通过"}:
            reasons.append("reviewer_borderline_or_reject")
        if any(item.status == "fail" for item in reviewer_summary.hard_gates):
            reasons.append("reviewer_hard_gate_fail")
        if len(reviewer_summary.key_issues) >= 3:
            reasons.append("reviewer_many_key_issues")

    if reasons:
        return True, "; ".join(reasons)
    return False, "auto: reviewer stable without high-risk or strict-review signals"
