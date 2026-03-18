"""Persistent JSON store for education platform domain data."""

from datetime import datetime, timezone
import json
import shutil
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
        "course_blueprints": {},
        "course_packages": {},
        "assets": {},
        "extractions": {},
        "feedback": {},
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

    def _root_dir(self) -> Path:
        root = get_paths().base_dir / STORE_SUBDIR
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _state_path(self) -> Path:
        return self._root_dir() / STORE_FILE

    def _backup_path(self) -> Path:
        return self._root_dir() / "state.bak.json"

    def _snapshot_dir(self) -> Path:
        snapshot_dir = self._root_dir() / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        return snapshot_dir

    @staticmethod
    def _merge_with_defaults(raw: dict[str, Any]) -> dict[str, Any]:
        state = _default_state()
        state.update(raw)
        return state

    @staticmethod
    def _compact_state(state: dict[str, Any]) -> dict[str, Any]:
        compacted = _default_state()
        compacted.update(state)

        logs = compacted.get("audit_logs")
        if isinstance(logs, list) and len(logs) > 5000:
            compacted["audit_logs"] = logs[-5000:]

        run_signals = compacted.get("run_signals")
        if isinstance(run_signals, dict):
            trimmed: dict[str, Any] = {}
            for run_id, signals in run_signals.items():
                if isinstance(signals, list):
                    trimmed[run_id] = signals[-24:]
            compacted["run_signals"] = trimmed

        return compacted

    def _load_json(self, path: Path) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("Education state file must be a JSON object")
        return self._merge_with_defaults(raw)

    def _write_snapshot(self, state: dict[str, Any]) -> None:
        snapshot_name = f"state-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        snapshot_path = self._snapshot_dir() / snapshot_name
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        snapshots = sorted(self._snapshot_dir().glob("state-*.json"))
        if len(snapshots) > 20:
            for stale in snapshots[:-20]:
                stale.unlink(missing_ok=True)

    def _recover_from_backup(self) -> dict[str, Any] | None:
        candidates = [self._backup_path()]
        candidates.extend(sorted(self._snapshot_dir().glob("state-*.json"), reverse=True))
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                return self._load_json(candidate)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        return None

    def read_state(self) -> dict[str, Any]:
        path = self._state_path()
        if not path.exists():
            state = _default_state()
            self.write_state(state)
            return state
        try:
            return self._load_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            recovered = self._recover_from_backup()
            if recovered is not None:
                self.write_state(recovered)
                return recovered
            return _default_state()

    def write_state(self, state: dict[str, Any]) -> None:
        path = self._state_path()
        backup_path = self._backup_path()
        temp = path.with_suffix(".tmp")
        compacted = self._compact_state(state)
        if path.exists():
            try:
                shutil.copy2(path, backup_path)
            except OSError:
                pass
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(compacted, f, ensure_ascii=False, indent=2)
        temp.replace(path)
        self._write_snapshot(compacted)

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
