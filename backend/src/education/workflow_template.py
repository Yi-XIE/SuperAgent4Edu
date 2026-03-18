"""Workflow template helpers for education state machine."""

from __future__ import annotations

from typing import Any

from .schemas import EducationRunState

_STAGE_ALIASES = {
    "blueprint": "Blueprint",
    "stage1": "Blueprint",
    "ubd stage 1": "Blueprint",
    "package": "Package",
    "stage2": "Package",
    "stage3": "Package",
    "presentation": "Package",
    "learning-kit": "Package",
    "learning kit": "Package",
    "reviewer": "Reviewer",
    "critic": "Critic",
}


def get_workflow_template_content(state: dict, run: EducationRunState) -> dict[str, Any] | None:
    template_id = run.workflow_template_id
    if not template_id:
        return None
    raw = state.get("templates", {}).get(template_id)
    if not isinstance(raw, dict):
        return None
    if raw.get("org_id") != run.org_id:
        return None
    content = raw.get("content")
    if not isinstance(content, dict):
        return None
    return content


def normalize_stage(stage: str) -> str | None:
    value = stage.strip().lower()
    if not value:
        return None
    if value in _STAGE_ALIASES:
        return _STAGE_ALIASES[value]
    for key, mapped in _STAGE_ALIASES.items():
        if key in value:
            return mapped
    return None


def enabled_rerun_stages(template_content: dict[str, Any] | None) -> set[str]:
    if not template_content:
        return set()
    raw = template_content.get("enabled_stages")
    if not isinstance(raw, list):
        raw = template_content.get("nodes")
    if not isinstance(raw, list):
        return set()

    enabled: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        normalized = normalize_stage(item)
        if normalized is not None:
            enabled.add(normalized)
    return enabled


def resolve_rerun_map_override(
    template_content: dict[str, Any] | None,
    checkpoint_id: str,
) -> dict[str, list[str]]:
    if not template_content:
        return {}
    rerun_map = template_content.get("rerun_map")
    if not isinstance(rerun_map, dict):
        return {}
    checkpoint_map = rerun_map.get(checkpoint_id)
    if not isinstance(checkpoint_map, dict):
        return {}

    resolved: dict[str, list[str]] = {}
    for option, targets in checkpoint_map.items():
        if not isinstance(option, str):
            continue
        if not isinstance(targets, list):
            continue
        normalized_targets: list[str] = []
        for target in targets:
            if not isinstance(target, str):
                continue
            stage = normalize_stage(target)
            if stage is None:
                continue
            normalized_targets.append(stage)
        resolved[option] = normalized_targets
    return resolved


def checkpoint_enabled(
    template_content: dict[str, Any] | None,
    checkpoint_id: str,
    default: bool = True,
) -> bool:
    if not template_content:
        return default
    checkpoints = template_content.get("checkpoints")
    if not isinstance(checkpoints, dict):
        return default
    value = checkpoints.get(checkpoint_id)
    if isinstance(value, bool):
        return value
    short_key = checkpoint_id.replace("-asset-extraction-confirm", "")
    value = checkpoints.get(short_key)
    if isinstance(value, bool):
        return value
    return default


def guard_max_local_rework(
    template_content: dict[str, Any] | None,
    default: int,
) -> int:
    if not template_content:
        return default

    guard = template_content.get("guard")
    if isinstance(guard, dict):
        value = guard.get("max_local_rework")
        if isinstance(value, int) and value >= 0:
            return value

    rerun_guard = template_content.get("rerun_guard")
    if isinstance(rerun_guard, str):
        marker = "max_local_rework="
        if marker in rerun_guard:
            try:
                parsed = int(rerun_guard.split(marker, 1)[1].strip())
            except ValueError:
                parsed = default
            if parsed >= 0:
                return parsed
    return default
