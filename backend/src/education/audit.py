"""Audit logging helpers for education APIs."""

from .schemas import ActorContext, AuditLogEntry
from .store import EducationStore

_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "token",
    "secret",
    "password",
}


def _sanitize_details(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(token in key_lower for token in _SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = _sanitize_details(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_details(item) for item in value]
    if isinstance(value, str) and len(value) > 2048:
        return value[:2048] + "...[truncated]"
    return value


def write_audit_log(
    store: EducationStore,
    *,
    actor: ActorContext,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> None:
    entry = AuditLogEntry(
        id=store.generate_id("audit"),
        org_id=actor.org_id,
        user_id=actor.user_id,
        role=actor.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=_sanitize_details(details or {}),
    )

    def _mutate(state: dict):
        logs = state["audit_logs"]
        logs.append(entry.model_dump())
        if len(logs) > 5000:
            del logs[:-5000]
        return None

    store.transaction(_mutate)
