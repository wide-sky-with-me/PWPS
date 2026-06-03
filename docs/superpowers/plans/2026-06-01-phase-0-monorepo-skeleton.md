# Phase 0 Monorepo Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable pWPS Agent project skeleton required by Phase 0.

**Architecture:** Create a monorepo with a FastAPI backend in `apps/api`, a Next.js frontend in `apps/web`, shared root workspace config, Docker Compose infrastructure, and local environment documentation. Keep business logic out of Phase 0 except for basic service health endpoints and a simple home page proving the stack runs.

**Tech Stack:** `uv`, Python 3.12+, FastAPI, Pydantic v2, pytest, ruff, mypy, `pnpm`, Next.js App Router, TypeScript, Docker Compose, PostgreSQL, Redis.

---

### Task 1: Backend Health Skeleton

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/pwps_agent_api/__init__.py`
- Create: `apps/api/src/pwps_agent_api/main.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from pwps_agent_api.main import app


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
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "service": "pwps-agent-api",
        "status": "ready",
        "checks": {
            "configuration": "ok",
        },
    }
```

- [ ] **Step 2: Run test to verify it fails before implementation**

Run: `cd apps/api && uv run pytest tests/test_health.py -q`
Expected: FAIL because `pwps_agent_api.main` does not exist yet.

- [ ] **Step 3: Implement the minimal FastAPI app**

```python
from typing import Any

from fastapi import FastAPI

APP_VERSION = "0.1.0"

app = FastAPI(
    title="pWPS Agent API",
    version=APP_VERSION,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "service": "pwps-agent-api",
        "status": "ok",
        "version": APP_VERSION,
    }


@app.get("/ready")
def ready() -> dict[str, Any]:
    return {
        "service": "pwps-agent-api",
        "status": "ready",
        "checks": {
            "configuration": "ok",
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && uv run pytest tests/test_health.py -q`
Expected: PASS.

### Task 2: Frontend Workspace Skeleton

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/page.tsx`

- [ ] **Step 1: Add frontend config and a minimal home page**

The home page must identify the product as pWPS Agent and avoid adding workflow behavior before the API and schema exist.

- [ ] **Step 2: Run frontend typecheck**

Run: `pnpm --filter web typecheck`
Expected: PASS after dependencies are installed.

### Task 3: Infrastructure and Environment Contract

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Add PostgreSQL and Redis compose services**

Compose should expose local PostgreSQL on `5432` and Redis on `6379`, matching `docs/tech_stack.md`.

- [ ] **Step 2: Add `.env.example` with non-secret placeholders**

Environment variables must match `docs/deployment_guide.md` and must not include real API keys.

- [ ] **Step 3: Document local startup commands**

The README must show `pnpm install`, `cd apps/api && uv sync`, API health, web dev, and infra startup commands.

### Task 4: Verification

**Files:**
- Verify: `apps/api/pyproject.toml`
- Verify: `apps/api/tests/test_health.py`
- Verify: `apps/web/package.json`
- Verify: `infra/docker-compose.yml`

- [ ] **Step 1: Run backend checks**

Run:

```bash
cd apps/api
uv run pytest
uv run ruff check .
uv run mypy .
```

- [ ] **Step 2: Run frontend checks**

Run:

```bash
pnpm install
pnpm --filter web typecheck
```

- [ ] **Step 3: Record any commands blocked by network or missing services**

If dependency installation cannot run in the sandbox, report that clearly and leave the generated config ready for a normal developer environment.

---

## Self-Review

- Spec coverage: Covers Phase 0 deliverables from `development_stages.md`: `apps/web`, `apps/api`, `infra/docker-compose.yml`, `.env.example`, and startup documentation. It also adds API health and readiness endpoints from `deployment_guide.md`.
- Placeholder scan: No `TBD` or unspecified implementation steps remain.
- Type consistency: Backend package name is consistently `pwps_agent_api`; frontend package name is consistently `web`.
