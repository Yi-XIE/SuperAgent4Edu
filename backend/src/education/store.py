"""Persistent JSON store for education platform domain data."""

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from src.config.paths import get_paths

STORE_SUBDIR = "education"
STORE_FILE = "state.json"


def _default_state() -> dict[str, Any]:
    return {
        "orgs": {},
        "projects": {},
        "runs": {},
        "templates": {},
        "resources": {},
        "student_tasks": {},
        "student_submissions": {},
        "run_signals": {},
        "audit_logs": [],
    }


class EducationStore:
    def __init__(self):
        self._lock = threading.Lock()

    def _state_path(self) -> Path:
        root = get_paths().base_dir / STORE_SUBDIR
        root.mkdir(parents=True, exist_ok=True)
        return root / STORE_FILE

    def read_state(self) -> dict[str, Any]:
        path = self._state_path()
        if not path.exists():
            state = _default_state()
            self.write_state(state)
            return state
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                return _default_state()
            state = _default_state()
            state.update(raw)
            return state
        except (OSError, json.JSONDecodeError):
            return _default_state()

    def write_state(self, state: dict[str, Any]) -> None:
        path = self._state_path()
        temp = path.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        temp.replace(path)

    def transaction(self, mutator):
        with self._lock:
            state = self.read_state()
            result = mutator(state)
            self.write_state(state)
            return result

    @staticmethod
    def generate_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def ensure_org(self, org_id: str, name: str = "Default Org") -> dict[str, Any]:
        def _mutate(state: dict[str, Any]):
            orgs = state["orgs"]
            org = orgs.get(org_id)
            if org is None:
                org = {
                    "id": org_id,
                    "name": name,
                    "description": "Auto-created default education org",
                    "members": [],
                }
                orgs[org_id] = org
            return org

        return self.transaction(_mutate)


_store: EducationStore | None = None


def get_education_store() -> EducationStore:
    global _store
    if _store is None:
        _store = EducationStore()
    return _store
