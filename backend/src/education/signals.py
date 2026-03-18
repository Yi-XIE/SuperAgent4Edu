"""Education memory signal extraction and run-level usage tracking."""

from typing import Any

from .schemas import MemorySignalUsage
from .store import get_education_store

EDUCATION_FACT_CATEGORIES = {
    "teacher_preference",
    "course_continuity",
    "learning_kit_preference",
    "team_template",
}


def extract_education_signals(memory_data: dict[str, Any]) -> list[dict[str, Any]]:
    facts = memory_data.get("facts", [])
    if not isinstance(facts, list):
        return []

    result: list[dict[str, Any]] = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        category = fact.get("category")
        content = fact.get("content")
        if category not in EDUCATION_FACT_CATEGORIES:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        confidence = fact.get("confidence")
        result.append(
            {
                "category": category,
                "content": content.strip(),
                "confidence": float(confidence) if isinstance(confidence, (int, float)) else 0.0,
            }
        )

    result.sort(key=lambda item: item["confidence"], reverse=True)
    return result[:8]


def record_used_signals(run_id: str, signals: list[dict[str, Any]], source: str = "memory_injection") -> list[dict[str, Any]]:
    store = get_education_store()
    usage = [
        MemorySignalUsage(
            category=item.get("category", "unknown"),
            content=item.get("content", ""),
            confidence=float(item.get("confidence", 0.0)),
            source=source,
        ).model_dump()
        for item in signals
        if item.get("content")
    ]

    def _mutate(state: dict[str, Any]):
        existing = state["run_signals"].get(run_id, [])
        merged_keyed = {
            (entry["category"], entry["content"], entry.get("source", source)): entry for entry in existing
        }
        for entry in usage:
            merged_keyed[(entry["category"], entry["content"], entry.get("source", source))] = entry
        merged = list(merged_keyed.values())
        merged.sort(key=lambda item: (item.get("confidence", 0.0), item.get("used_at", "")), reverse=True)
        state["run_signals"][run_id] = merged[:12]
        return state["run_signals"][run_id]

    return store.transaction(_mutate)


def get_used_signals(run_id: str) -> list[dict[str, Any]]:
    store = get_education_store()
    state = store.read_state()
    entries = state.get("run_signals", {}).get(run_id, [])
    return [entry for entry in entries if isinstance(entry, dict)]
