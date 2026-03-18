"""Pre-run retrieval snapshot contracts."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from src.education.schemas import ActorContext, CreateRunRequest
from src.gateway.routers.education_projects import create_project_run


class DummyStore:
    def __init__(self, state: dict):
        self.state = deepcopy(state)
        self._counter = 0

    def read_state(self) -> dict:
        return self.state

    def transaction(self, mutator):
        return mutator(self.state)

    def generate_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


def _state() -> dict:
    return {
        "orgs": {},
        "projects": {
            "proj_1": {
                "id": "proj_1",
                "org_id": "org_1",
                "name": "课程项目",
                "description": "",
                "owner_id": "teacher_1",
                "status": "draft",
                "version": 1,
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            }
        },
        "runs": {},
        "course_blueprints": {},
        "course_packages": {},
        "assets": {
            "asset_1": {
                "id": "asset_1",
                "org_id": "org_1",
                "asset_type": "activity_idea",
                "title": "高复用探究活动",
                "content": "活动内容",
                "tags": ["PBL"],
                "grade_band": "elementary",
                "domain_focus": [],
                "source_run_id": None,
                "source_path": None,
                "confidence": 0.8,
                "usage_count": 5,
                "visibility": "private",
                "status": "active",
                "created_by": "teacher_1",
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            }
        },
        "extractions": {},
        "feedback": {},
        "templates": {},
        "resources": {
            "res_white": {
                "id": "res_white",
                "org_id": "org_1",
                "title": "白名单资源",
                "url": "https://example.com/white",
                "source_type": "article",
                "tags": ["AI"],
                "whitelisted": True,
                "summary": "可信来源",
                "created_by": "teacher_1",
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            },
            "res_black": {
                "id": "res_black",
                "org_id": "org_1",
                "title": "非白名单资源",
                "url": "https://example.com/black",
                "source_type": "article",
                "tags": ["AI"],
                "whitelisted": False,
                "summary": "不应召回",
                "created_by": "teacher_1",
                "created_at": "2026-03-18T00:00:00+00:00",
                "updated_at": "2026-03-18T00:00:00+00:00",
            },
        },
        "student_tasks": {},
        "student_submissions": {},
        "run_signals": {},
        "audit_logs": [],
    }


@pytest.mark.anyio
async def test_create_run_writes_pre_retrieval_snapshot_with_whitelist_filter():
    store = DummyStore(_state())
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")

    payload = CreateRunRequest(
        org_id="org_1",
        project_id="proj_1",
        title="课程运行",
        generation_mode="material_first",
    )
    with patch("src.gateway.routers.education_projects.get_education_store", return_value=store):
        created = await create_project_run("proj_1", payload, actor)

    assert created.retrieval_snapshot_at is not None
    assert "asset_1" in created.selected_asset_ids
    assert any("白名单资源" in note for note in created.asset_retrieval_notes)
    assert all("非白名单资源" not in note for note in created.asset_retrieval_notes)
