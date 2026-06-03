from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from pwps_agent_api.main import app, get_readiness_checker

client = TestClient(app)


def test_health_returns_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "pwps-agent-api",
        "status": "ok",
        "version": "0.1.0",
    }


def test_ready_returns_local_readiness_status() -> None:
    class StubReadinessChecker:
        async def check(self) -> dict[str, str]:
            return {"configuration": "ok", "database": "ok", "redis": "ok"}

    async def override_get_readiness_checker() -> AsyncIterator[StubReadinessChecker]:
        yield StubReadinessChecker()

    app.dependency_overrides[get_readiness_checker] = override_get_readiness_checker
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "service": "pwps-agent-api",
        "status": "ready",
        "checks": {
            "configuration": "ok",
            "database": "ok",
            "redis": "ok",
        },
    }
    app.dependency_overrides.clear()
