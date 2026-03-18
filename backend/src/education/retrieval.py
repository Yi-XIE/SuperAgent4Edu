"""Pre-run asset retrieval snapshot helpers."""

from __future__ import annotations

import re

from .schemas import EducationResource, EducationRunState, TeachingAsset, utc_now_iso


def _tokenize(value: str) -> set[str]:
    if not value:
        return set()
    tokens = {
        token
        for token in re.findall(r"[\w\u4e00-\u9fff]+", value.lower())
        if len(token) >= 2
    }
    return tokens


def _match_count(query_tokens: set[str], text: str) -> int:
    if not query_tokens:
        return 0
    haystack = text.lower()
    return sum(1 for token in query_tokens if token in haystack)


def _asset_score(run: EducationRunState, query_tokens: set[str], asset: TeachingAsset) -> tuple[float, int]:
    searchable = " ".join([asset.title, asset.content, " ".join(asset.tags), " ".join(asset.domain_focus)])
    relevance = _match_count(query_tokens, searchable)
    mode_bonus = 1.0 if run.generation_mode == "material_first" else 0.0
    score = (relevance * 3.0) + (asset.usage_count * (1.3 + mode_bonus)) + asset.confidence
    return score, relevance


def _resource_score(run: EducationRunState, query_tokens: set[str], resource: EducationResource) -> tuple[float, int]:
    searchable = " ".join([resource.title, resource.summary, " ".join(resource.tags)])
    relevance = _match_count(query_tokens, searchable)
    mode_bonus = 0.4 if run.generation_mode in {"material_first", "mixed"} else 0.0
    score = (relevance * 2.5) + mode_bonus
    return score, relevance


def prepare_pre_run_asset_retrieval(state: dict, run: EducationRunState) -> None:
    """Refresh retrieval notes and selected assets before CP1.

    This snapshot is intentionally lightweight and deterministic so it can be
    asserted by API-level tests without model participation.
    """
    query_tokens = _tokenize(
        " ".join(
            [
                run.title,
                run.details or "",
                " ".join(run.asset_retrieval_notes),
                run.generation_mode,
            ]
        )
    )

    assets: list[TeachingAsset] = []
    for raw in state.get("assets", {}).values():
        if not isinstance(raw, dict):
            continue
        if raw.get("org_id") != run.org_id:
            continue
        if raw.get("status", "active") != "active":
            continue
        assets.append(TeachingAsset(**raw))
    ranked_assets = []
    for asset in assets:
        score, relevance = _asset_score(run, query_tokens, asset)
        ranked_assets.append((score, relevance, asset))
    ranked_assets.sort(key=lambda row: (row[0], row[2].usage_count, row[2].updated_at), reverse=True)

    whitelisted_resources: list[EducationResource] = []
    for raw in state.get("resources", {}).values():
        if not isinstance(raw, dict):
            continue
        if raw.get("org_id") != run.org_id:
            continue
        if not bool(raw.get("whitelisted", True)):
            continue
        whitelisted_resources.append(EducationResource(**raw))
    ranked_resources = []
    for resource in whitelisted_resources:
        score, relevance = _resource_score(run, query_tokens, resource)
        ranked_resources.append((score, relevance, resource))
    ranked_resources.sort(key=lambda row: (row[0], row[2].updated_at), reverse=True)

    notes: list[str] = []
    selected_asset_ids: list[str] = []

    for score, relevance, asset in ranked_assets[:4]:
        reason = "任务相关" if relevance > 0 else "复用表现"
        notes.append(f"素材：{asset.title}（{reason}，复用 {asset.usage_count} 次，评分 {score:.1f}）")
        selected_asset_ids.append(asset.id)

    for score, relevance, resource in ranked_resources[:3]:
        reason = "任务相关" if relevance > 0 else "白名单补充"
        notes.append(f"资源：{resource.title}（{reason}，评分 {score:.1f}）")

    if not notes:
        mode_hint = (
            "优先按素材复用策略推进。"
            if run.generation_mode == "material_first"
            else "暂无可复用素材，按从零生成策略推进。"
        )
        notes = [mode_hint]

    run.asset_retrieval_notes = notes
    run.selected_asset_ids = selected_asset_ids
    run.retrieval_snapshot_at = utc_now_iso()
