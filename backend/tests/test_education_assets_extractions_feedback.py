"""Router-level tests for education asset/extraction/feedback APIs."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from src.education.schemas import ActorContext, CreateTeachingAssetRequest, CreateTeachingFeedbackRequest, EducationRunState, UpsertExtractionRequest
from src.gateway.routers.education_assets import create_asset, list_assets
from src.gateway.routers.education_extractions import get_extraction_candidates, upsert_or_confirm_extractions
from src.gateway.routers.education_feedback import create_feedback, list_feedback


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


def _base_state() -> dict:
    run = EducationRunState(
        id="run_1",
        org_id="org_1",
        project_id="proj_1",
        title="测试运行",
        artifact_paths=[
            "/mnt/user-data/outputs/lesson-plan.md",
            "/mnt/user-data/outputs/learning-kit-appendix.md",
        ],
    )
    return {
        "orgs": {},
        "projects": {"proj_1": {"id": "proj_1", "org_id": "org_1", "name": "p", "owner_id": "u"}},
        "runs": {"run_1": run.model_dump()},
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


@pytest.mark.anyio
async def test_assets_create_and_list():
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    store = DummyStore(_base_state())

    payload = CreateTeachingAssetRequest(
        org_id="org_1",
        asset_type="activity_idea",
        title="探究活动模板",
        content="活动内容",
        tags=["PBL"],
        source_run_id="run_1",
    )
    with patch("src.gateway.routers.education_assets.get_education_store", return_value=store):
        created = await create_asset(payload, actor)
        listed = await list_assets(actor=actor)

    assert created.org_id == "org_1"
    assert created.asset_type == "activity_idea"
    assert len(listed) == 1
    assert listed[0].title == "探究活动模板"


@pytest.mark.anyio
async def test_extractions_generate_and_confirm_to_assets():
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    store = DummyStore(_base_state())

    with patch("src.gateway.routers.education_extractions.get_education_store", return_value=store):
        generated = await get_extraction_candidates("run_1", actor)
        assert len(generated) >= 1

        confirmed = await upsert_or_confirm_extractions(
            "run_1",
            UpsertExtractionRequest(mode="confirm", option="一键入库"),
            actor,
        )

    assert len(confirmed) >= 1
    accepted = [item for item in confirmed if item.status == "accepted"]
    assert len(accepted) >= 1
    assert len(store.state["assets"]) >= 1
    run = EducationRunState(**store.state["runs"]["run_1"])
    assert run.asset_extraction_status == "confirmed"
    assert run.status == "accepted"


@pytest.mark.anyio
async def test_feedback_increments_asset_usage():
    actor = ActorContext(user_id="teacher_1", org_id="org_1", role="teacher")
    state = _base_state()
    state["assets"]["asset_1"] = {
        "id": "asset_1",
        "org_id": "org_1",
        "asset_type": "activity_idea",
        "title": "活动卡",
        "content": "内容",
        "tags": [],
        "grade_band": "elementary",
        "domain_focus": [],
        "source_run_id": "run_1",
        "source_path": None,
        "confidence": 0.7,
        "usage_count": 0,
        "visibility": "private",
        "status": "active",
        "created_by": "teacher_1",
        "created_at": "2026-03-18T00:00:00+00:00",
        "updated_at": "2026-03-18T00:00:00+00:00",
    }
    store = DummyStore(state)

    payload = CreateTeachingFeedbackRequest(
        org_id="org_1",
        run_id="run_1",
        summary="课堂反馈良好",
        asset_ids=["asset_1"],
    )
    with patch("src.gateway.routers.education_feedback.get_education_store", return_value=store):
        created = await create_feedback(payload, actor)
        listed = await list_feedback(actor=actor)

    assert created.run_id == "run_1"
    assert len(listed) == 1
    assert listed[0].summary == "课堂反馈良好"
    assert store.state["assets"]["asset_1"]["usage_count"] == 1
