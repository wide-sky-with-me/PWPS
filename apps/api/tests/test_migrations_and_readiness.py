import os
import sqlite3
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pwps_agent_api.core.readiness import ApplicationReadinessChecker
from pwps_agent_api.db.base import Base
from pwps_agent_api.main import app, get_readiness_checker


def test_alembic_migration_files_define_runs_table() -> None:
    api_root = Path(__file__).resolve().parents[1]
    alembic_ini = api_root / "alembic.ini"
    env_py = api_root / "migrations" / "env.py"
    migration_files = sorted((api_root / "migrations" / "versions").glob("*.py"))

    assert alembic_ini.exists()
    assert env_py.exists()
    assert migration_files
    migration_text = "\n".join(path.read_text(encoding="utf-8") for path in migration_files)
    assert "create_table" in migration_text
    assert "runs" in migration_text
    assert "workflow_state_json" in migration_text
    assert "outputs_json" in migration_text
    assert "trace_json" in migration_text
    assert "pending_decision_json" in migration_text


def test_alembic_upgrade_head_applies_pending_decision_column(tmp_path: Path) -> None:
    api_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration.db"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }

    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=api_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("pragma table_info(runs)").fetchall()}
    assert "pending_decision_json" in columns


@pytest.mark.anyio
async def test_application_readiness_checker_reports_database_and_redis_ok(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ready.db'}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    checker = ApplicationReadinessChecker(sessionmaker, FakeRedis())

    assert await checker.check() == {
        "configuration": "ok",
        "database": "ok",
        "redis": "ok",
    }

    await engine.dispose()


def test_ready_endpoint_uses_readiness_checker() -> None:
    class StubReadinessChecker:
        async def check(self) -> dict[str, str]:
            return {"configuration": "ok", "database": "ok", "redis": "ok"}

    async def override_get_readiness_checker() -> AsyncIterator[StubReadinessChecker]:
        yield StubReadinessChecker()

    app.dependency_overrides[get_readiness_checker] = override_get_readiness_checker
    client = TestClient(app)

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


class FakeRedis:
    async def ping(self, **_: object) -> bool:
        return True
