# Phase 6 Local Document Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-document retrieval path that produces normalized, field-attached evidence for Auto and Guided Draft workflows.

**Architecture:** Keep retrieval source-specific behavior in `knowledge/local_document.py`, normalization in `knowledge/normalizer.py`, and fallback orchestration in `knowledge/service.py`. The workflow asks `KnowledgeService` for evidence and remains responsible only for attaching returned evidence to workflow state. Local documents are a bundled JSON simple index for this phase; Qdrant, MinIO, and complex parsing remain out of scope.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, JSON local index.

---

### Task 1: Knowledge Schemas and Local Provider

**Files:**
- Modify: `apps/api/src/pwps_agent_api/schemas/models.py`
- Modify: `apps/api/src/pwps_agent_api/schemas/__init__.py`
- Create: `apps/api/src/pwps_agent_api/knowledge/local_document.py`
- Create: `apps/api/data/knowledge_base/local_documents.json`
- Create: `apps/api/tests/test_knowledge_service.py`

- [x] Add failing provider tests for field-tag filtering and section metadata.
- [x] Run `uv run pytest tests/test_knowledge_service.py -q` and confirm the missing module failure.
- [x] Add `KnowledgeQuery`, `KnowledgeHit`, explicit evidence `section_path`, and the JSON-backed local provider.
- [x] Run `uv run pytest tests/test_knowledge_service.py -q`.

### Task 2: Evidence Normalization and Fallback Service

**Files:**
- Create: `apps/api/src/pwps_agent_api/knowledge/normalizer.py`
- Create: `apps/api/src/pwps_agent_api/knowledge/service.py`
- Modify: `apps/api/src/pwps_agent_api/knowledge/__init__.py`
- Modify: `apps/api/tests/test_knowledge_service.py`

- [x] Add failing tests for normalized local evidence and model-prior fallback for uncovered fields.
- [x] Implement `EvidenceNormalizer` and `KnowledgeService`.
- [x] Run `uv run pytest tests/test_knowledge_service.py -q`.

### Task 3: Workflow Integration

**Files:**
- Modify: `apps/api/src/pwps_agent_api/workflow/auto.py`
- Modify: `apps/api/src/pwps_agent_api/workflow/guided.py`
- Modify: `apps/api/src/pwps_agent_api/skills/candidate_generation.py`
- Modify: `apps/api/tests/test_auto_draft_workflow.py`
- Modify: `apps/api/tests/test_guided_run_api.py`
- Modify: `README.md`

- [x] Add failing workflow assertions for local-document evidence attachment and UI-facing Guided evidence.
- [x] Replace direct model-prior calls with `KnowledgeService`.
- [x] Source committed candidates from their strongest attached evidence and describe evidence-backed candidates accurately.
- [x] Update README Phase status.
- [x] Run backend tests, Ruff, and mypy.

---

## Self-Review

- Spec coverage: Adds Local Document Provider, EvidenceNormalizer, source/section/content/limitations, field evidence attachment, and UI-facing Guided evidence.
- Scope: Uses a JSON simple index and preserves model-prior fallback. It does not add vector search or document parsing.
- Boundary check: KnowledgeService returns evidence only; CandidateGenerationSkill still proposes candidates and DecisionActor still selects values.

## Verification Record

- `uv run pytest -q`: `25 passed`, with one upstream Starlette `httpx` deprecation warning.
- `uv run ruff check .`: passed.
- `uv run mypy .`: passed.
- `pnpm --filter web lint`: passed.
- `pnpm --filter web typecheck`: passed.
- `pnpm --filter web build`: passed.
- Browser automation was not run because Python Playwright and a local Redis runtime are not installed in this workspace environment.
