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


def test_create_run_and_fetch_status_outputs_and_events(tmp_path: Path) -> None:
    event_store = RecordingEventStore()
    client = _build_test_client(tmp_path, event_store=event_store)

    create_response = client.post(
        "/api/runs",
        json={"input": SAMPLE_INPUT, "mode": "auto", "attachments": []},
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["status"] == "finished"
    run_id = create_payload["run_id"]
    assert run_id in event_store.published_events
    assert {event.event for event in event_store.published_events[run_id]} >= {
        "normalize_input",
        "global_audit",
        "finalize_output",
    }

    status_response = client.get(f"/api/runs/{run_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["run_id"] == run_id
    assert status_payload["status"] == "finished"
    assert status_payload["mode"] == "auto"
    assert status_payload["publishability"] == "needs_confirmation"

    outputs_response = client.get(f"/api/runs/{run_id}/outputs")
    assert outputs_response.status_code == 200
    outputs_payload = outputs_response.json()
    assert outputs_payload["publishability"] == "needs_confirmation"
    assert outputs_payload["pwps"]["fields"]["base_material"]["value"] == "Q345R"
    assert outputs_payload["pwps"]["fields"]["project_name"]["value"] is None
    assert outputs_payload["field_report"]["field_states"]["consumable"]["value"] == "ER50-6"
    assert outputs_payload["risk_report"]["issues"]
    assert outputs_payload["discussion_trace"]["trace"]
    assert outputs_payload["evidence_report"]["evidence"]

    events_response = client.get(f"/api/runs/{run_id}/events")
    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert {event["event"] for event in events_payload["events"]} >= {
        "normalize_input",
        "global_audit",
        "finalize_output",
    }


def test_missing_run_returns_structured_error(tmp_path: Path) -> None:
    client = _build_test_client(tmp_path)

    response = client.get("/api/runs/run-missing")

    assert response.status_code == 404
    assert response.json() == {
        "error_code": "RUN_NOT_FOUND",
        "message": "Run not found.",
        "details": {"run_id": "run-missing"},
    }


def test_events_endpoint_falls_back_to_persisted_trace_when_event_store_is_empty(
    tmp_path: Path,
) -> None:
    client = _build_test_client(tmp_path, event_store=RecordingEventStore())
    create_response = client.post(
        "/api/runs",
        json={"input": SAMPLE_INPUT, "mode": "auto", "attachments": []},
    )
    run_id = create_response.json()["run_id"]

    fallback_store = RecordingEventStore()
    app.dependency_overrides[get_event_store] = lambda: fallback_store

    response = client.get(f"/api/runs/{run_id}/events")

    assert response.status_code == 200
    assert {event["event"] for event in response.json()["events"]} >= {
        "normalize_input",
        "global_audit",
        "finalize_output",
    }
    app.dependency_overrides.clear()


class RecordingEventStore:
    def __init__(self) -> None:
        self.published_events: dict[str, list[TraceEvent]] = {}

    async def publish_many(self, run_id: str, events: list[TraceEvent]) -> None:
        self.published_events[run_id] = events

    async def list_events(self, run_id: str) -> list[TraceEvent]:
        return self.published_events.get(run_id, [])


def _build_test_client(
    tmp_path: Path,
    event_store: RecordingEventStore | None = None,
) -> TestClient:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'runs.db'}"
    engine = create_async_engine(database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        try:
            async with sessionmaker() as session:
                yield session
        finally:
            await engine.dispose()

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_event_store] = lambda: event_store or RecordingEventStore()
    return TestClient(app)
