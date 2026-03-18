"""Security/governance guard tests for education APIs."""

from fastapi import HTTPException

from src.education.audit import _sanitize_details
from src.gateway.routers.resources import _validate_resource_url


def test_audit_details_redact_sensitive_fields_recursively():
    sanitized = _sanitize_details(
        {
            "api_key": "secret-1",
            "payload": {
                "Authorization": "Bearer secret-2",
                "nested": [{"token": "secret-3"}, {"ok": True}],
            },
        }
    )
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["payload"]["Authorization"] == "***REDACTED***"
    assert sanitized["payload"]["nested"][0]["token"] == "***REDACTED***"
    assert sanitized["payload"]["nested"][1]["ok"] is True


def test_resource_url_validation_rejects_non_http():
    try:
        _validate_resource_url("file:///etc/passwd")
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400


def test_resource_url_validation_rejects_private_hosts():
    try:
        _validate_resource_url("http://127.0.0.1:8080/resource")
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
