# Phase 4 Guided Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persisted Guided Draft pending decisions and resume behavior through the documented API endpoints.

**Architecture:** Reuse the existing field registry, requirement understanding Skill, model-prior evidence, candidate generation Skill, audit engine, and JSON output builder. Persist a `PendingUserDecision` checkpoint on `RunRecord`, expose it through `/current-decision`, and advance one field group per `/decision` submission until the run is finalized.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async, Alembic, Redis events, pytest.

---

### Task 1: Guided API Contract Tests

**Files:**
- Create: `apps/api/tests/test_guided_run_api.py`
- Modify: `apps/api/src/pwps_agent_api/schemas/models.py`
- Modify: `apps/api/src/pwps_agent_api/schemas/api.py`

- [ ] Write failing tests for Guided run creation, current decision retrieval, user decision submission, persisted resume across requests, and final output after all groups are accepted.
- [ ] Run `uv run pytest tests/test_guided_run_api.py -q` and confirm failure because Guided mode is not implemented.

### Task 2: Persisted Pending Decision

**Files:**
- Modify: `apps/api/src/pwps_agent_api/db/models.py`
- Create: `apps/api/migrations/versions/20260601_0002_add_pending_decision.py`
- Create: `apps/api/src/pwps_agent_api/workflow/guided.py`

- [ ] Add nullable `pending_decision_json` to `RunRecord`.
- [ ] Add `PendingUserDecision` Pydantic model.
- [ ] Implement create, submit, advance, audit, and finalize functions for Guided runs.

### Task 3: Routes and Verification

**Files:**
- Modify: `apps/api/src/pwps_agent_api/services/run_service.py`
- Modify: `apps/api/src/pwps_agent_api/api/runs.py`
- Modify: `README.md`
- Modify: `docs/api_contract.md`

- [ ] Add `GET /api/runs/{run_id}/current-decision`.
- [ ] Add `POST /api/runs/{run_id}/decision`.
- [ ] Return structured `INVALID_STATE_TRANSITION` and `DECISION_SESSION_EXPIRED` errors.
- [ ] Run:

```bash
cd apps/api
uv run pytest
uv run ruff check .
uv run mypy .
```

---

## Self-Review

- Spec coverage: Implements the Phase 4 API and persistence checkpoint required by `workflow.md`, `api_contract.md`, and `development_stages.md`.
- Scope: This is persisted application-level checkpoint/resume. LangGraph durable checkpoint storage can be added after the Guided state contract is stable.
- Type consistency: Guided state remains `WorkflowState`; pending card is a Pydantic model persisted as JSON.
