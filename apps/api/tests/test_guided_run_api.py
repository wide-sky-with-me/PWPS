from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pwps_agent_api.db.base import Base
from pwps_agent_api.db.session import get_session
from pwps_agent_api.events.store import get_event_store
from pwps_agent_api.main import app
from pwps_agent_api.schemas import TraceEvent

SAMPLE_INPUT = "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案"


def test_guided_run_pauses_and_resumes_until_output_is_ready(tmp_path: Path) -> None:
    client = _build_test_client(tmp_path)

    create_response = client.post(
        "/api/runs",
        json={"input": SAMPLE_INPUT, "mode": "guided", "attachments": []},
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["status"] == "waiting_for_user"
    run_id = create_payload["run_id"]

    visited_groups: list[str] = []
    for _ in range(5):
        card_response = client.get(f"/api/runs/{run_id}/current-decision")
        assert card_response.status_code == 200
        card = card_response.json()
        visited_groups.append(card["target_group"])
        if card["target_group"] == "consumable_group":
            assert card["evidence"]
            assert {item["source_type"] for item in card["evidence"]} == {"local_document"}
            assert all(item["section_path"] for item in card["evidence"])
            assert all(item["limitations"] for item in card["evidence"])

        decision_response = client.post(
            f"/api/runs/{run_id}/decision",
            json={
                "session_id": card["session_id"],
                "decision_type": "accept_recommended",
                "selected_values": card["recommended"],
                "comment": "Accept current guided recommendation.",
            },
        )
        assert decision_response.status_code == 200
        assert decision_response.json()["accepted"] is True

    assert visited_groups == [
        "basic_condition_group",
        "consumable_group",
        "parameter_group",
        "thermal_group",
        "meta_group",
    ]

    status_response = client.get(f"/api/runs/{run_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "finished"

    outputs_response = client.get(f"/api/runs/{run_id}/outputs")
    assert outputs_response.status_code == 200
    assert outputs_response.json()["pwps"]["fields"]["base_material"]["value"] == "Q345R"
    assert outputs_response.json()["pwps"]["fields"]["project_name"]["value"] is None


def test_guided_decision_rejects_stale_session(tmp_path: Path) -> None:
    client = _build_test_client(tmp_path)
    create_response = client.post(
        "/api/runs",
        json={"input": SAMPLE_INPUT, "mode": "guided", "attachments": []},
    )
    run_id = create_response.json()["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/decision",
        json={
            "session_id": "session-stale",
            "decision_type": "accept_recommended",
            "selected_values": {},
            "comment": "This session is stale.",
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "DECISION_SESSION_EXPIRED"


def test_guided_hard_conflict_reenters_repair_target_and_finishes_after_correction(
    tmp_path: Path,
) -> None:
    client = _build_test_client(tmp_path)
    run_id = client.post(
        "/api/runs",
        json={"input": SAMPLE_INPUT, "mode": "guided", "attachments": []},
    ).json()["run_id"]

    for _ in range(5):
        card = client.get(f"/api/runs/{run_id}/current-decision").json()
        selected_values = card["recommended"]
        decision_type = "accept_recommended"
        if card["target_group"] == "consumable_group":
            selected_values = {**selected_values, "consumable": "J422"}
            decision_type = "override"
        response = client.post(
            f"/api/runs/{run_id}/decision",
            json={
                "session_id": card["session_id"],
                "decision_type": decision_type,
                "selected_values": selected_values,
                "comment": "Exercise the Guided repair loop.",
            },
        )
        assert response.status_code == 200

    assert response.json()["status"] == "waiting_for_user"
    repair_card = client.get(f"/api/runs/{run_id}/current-decision").json()
    assert repair_card["target_group"] == "consumable_group"
    assert repair_card["recommended"]["consumable"] == "ER50-6"

    repaired = client.post(
        f"/api/runs/{run_id}/decision",
        json={
            "session_id": repair_card["session_id"],
            "decision_type": "choose_alternative",
            "selected_values": repair_card["recommended"],
            "comment": "Replace J422 with the compatible wire.",
        },
    )

    assert repaired.status_code == 200
    assert repaired.json()["status"] == "finished"
    outputs = client.get(f"/api/runs/{run_id}/outputs").json()
    assert outputs["pwps"]["fields"]["consumable"]["value"] == "ER50-6"


def _build_test_client(tmp_path: Path) -> TestClient:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'guided-runs.db'}"
    engine = create_async_engine(database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    event_store = RecordingEventStore()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        try:
            async with sessionmaker() as session:
                yield session
        finally:
            await engine.dispose()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_event_store] = lambda: event_store
    return TestClient(app)


class RecordingEventStore:
    def __init__(self) -> None:
        self.published_events: dict[str, list[TraceEvent]] = {}

    async def publish_many(self, run_id: str, events: list[TraceEvent]) -> None:
        self.published_events.setdefault(run_id, []).extend(events)

    async def list_events(self, run_id: str) -> list[TraceEvent]:
        return self.published_events.get(run_id, [])
