# Phase 3 Run API Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Auto Draft runs and expose the Phase 3 FastAPI run endpoints.

**Architecture:** Keep route schemas in `schemas/api.py`, SQLAlchemy models/session setup in `db/`, persistence orchestration in `services/run_service.py`, and HTTP routes in `api/runs.py`. Reuse the Phase 2 Auto workflow as the execution engine, then persist `WorkflowState`, outputs, and trace events in a run record.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL-compatible JSON columns, SQLite async test database, pytest.

---

### Task 1: Run API Contract Tests

**Files:**
- Create: `apps/api/tests/test_run_api.py`
- Create: `apps/api/src/pwps_agent_api/schemas/api.py`
- Create: `apps/api/src/pwps_agent_api/api/runs.py`
- Modify: `apps/api/src/pwps_agent_api/main.py`

- [ ] **Step 1: Write failing API tests**

Tests must call:

```text
POST /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/outputs
GET /api/runs/{run_id}/events
```

and assert Pydantic enum values serialize as strings, output includes `pwps`, `field_report`, `risk_report`, `discussion_trace`, and missing runs return `RUN_NOT_FOUND`.

- [ ] **Step 2: Run tests to verify missing routes fail**

Run: `cd apps/api && uv run pytest tests/test_run_api.py -q`
Expected: FAIL because the API routes and DB dependencies do not exist yet.

### Task 2: SQLAlchemy Persistence

**Files:**
- Create: `apps/api/src/pwps_agent_api/core/config.py`
- Create: `apps/api/src/pwps_agent_api/db/base.py`
- Create: `apps/api/src/pwps_agent_api/db/models.py`
- Create: `apps/api/src/pwps_agent_api/db/session.py`
- Create: `apps/api/src/pwps_agent_api/services/run_service.py`
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add dependencies**

Add `sqlalchemy[asyncio]>=2.0.0`, `asyncpg>=0.30.0`, and `aiosqlite>=0.20.0`. `asyncpg` is for local PostgreSQL; `aiosqlite` is for isolated async route tests.

- [ ] **Step 2: Implement RunRecord model**

Persist:

```text
run_id
status
mode
raw_input
workflow_state_json
outputs_json
trace_json
created_at
updated_at
```

- [ ] **Step 3: Implement RunService**

`create_auto_run()` runs Phase 2 workflow, writes artifacts under local artifact dir, stores the serialized workflow state and output payloads, and returns `CreateRunResponse`.

### Task 3: Route Implementation and Verification

**Files:**
- Modify: `apps/api/src/pwps_agent_api/main.py`
- Modify: `README.md`

- [ ] **Step 1: Wire routes into the FastAPI app**

Include `/api/runs` router and keep `/health` and `/ready`.

- [ ] **Step 2: Update README**

Document `POST /api/runs` plus output retrieval endpoints.

- [ ] **Step 3: Run backend checks**

```bash
cd apps/api
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
```

---

## Self-Review

- Spec coverage: Covers the Phase 3 endpoint list from `development_stages.md` and `api_contract.md`: create run, get run, get outputs, and get events with persisted WorkflowState and TraceEvent data.
- Placeholder scan: No `TBD` or vague implementation steps remain.
- Type consistency: Route responses use Pydantic schemas and run state uses existing `WorkflowState`.
