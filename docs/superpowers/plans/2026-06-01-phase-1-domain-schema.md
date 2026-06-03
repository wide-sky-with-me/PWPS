# Phase 1 Domain Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Pydantic v2 domain schema layer and default field registry required by Phase 1.

**Architecture:** Keep schema definitions in `pwps_agent_api.schemas` with enums separated from model classes. Keep registry construction in `pwps_agent_api.fields.registry` so workflow code can later depend on a stable loader instead of hard-coded field lists.

**Tech Stack:** Python 3.12+, Pydantic v2, `StrEnum`, pytest, ruff, mypy.

---

### Task 1: Core Schema Models

**Files:**
- Create: `apps/api/src/pwps_agent_api/schemas/enums.py`
- Create: `apps/api/src/pwps_agent_api/schemas/models.py`
- Create: `apps/api/src/pwps_agent_api/schemas/__init__.py`
- Create: `apps/api/tests/test_schema_models.py`

- [ ] **Step 1: Write failing tests for schema validation and serialization**

Tests must cover enum-backed state, `extra="forbid"` validation, nested `WorkflowState` serialization, and high-risk human-confirmation metadata.

- [ ] **Step 2: Run tests to verify missing modules fail**

Run: `cd apps/api && uv run pytest tests/test_schema_models.py -q`
Expected: FAIL because `pwps_agent_api.schemas` does not exist yet.

- [ ] **Step 3: Implement minimal Pydantic models from `docs/data_schema.md`**

Implement `FieldSpec`, `FieldGroupSpec`, `FieldState`, `Evidence`, `DecisionContext`, `DecisionResult`, `DiscussionRound`, `DiscussionSession`, `AuditIssue`, `AuditResult`, `FieldTarget`, `TraceEvent`, and `WorkflowState`.

- [ ] **Step 4: Run schema tests to verify pass**

Run: `cd apps/api && uv run pytest tests/test_schema_models.py -q`
Expected: PASS.

### Task 2: Default Field Registry

**Files:**
- Create: `apps/api/src/pwps_agent_api/fields/__init__.py`
- Create: `apps/api/src/pwps_agent_api/fields/registry.py`
- Create: `apps/api/tests/test_field_registry.py`

- [ ] **Step 1: Write failing registry tests**

Tests must confirm all MVP groups load, field names are unique, group references point to known fields, `meta_group` fields use `PROVIDED_ONLY`, and the fixed confirmation order matches the MVP workflow.

- [ ] **Step 2: Run tests to verify missing registry fails**

Run: `cd apps/api && uv run pytest tests/test_field_registry.py -q`
Expected: FAIL because `pwps_agent_api.fields.registry` does not exist yet.

- [ ] **Step 3: Implement a default registry loader**

Expose `load_default_field_registry() -> FieldRegistry` where `FieldRegistry` contains `fields`, `groups`, `field_registry_version`, and helper methods `get_field()` / `get_group()` / `confirmation_queue()`.

- [ ] **Step 4: Run registry tests to verify pass**

Run: `cd apps/api && uv run pytest tests/test_field_registry.py -q`
Expected: PASS.

### Task 3: Verification

**Files:**
- Verify: all backend source and tests.

- [ ] **Step 1: Run backend checks**

```bash
cd apps/api
uv run pytest
uv run ruff check .
uv run mypy .
```

- [ ] **Step 2: Confirm Phase 1 scope boundaries**

Do not implement workflow nodes, LLM Skills, KnowledgeService, or AuditEngine in this phase. Those belong to later stages.

---

## Self-Review

- Spec coverage: Covers Phase 1 deliverables from `development_stages.md`: schema models, enum states, registry loading, serialization, and pure schema tests.
- Placeholder scan: No `TBD` or unspecified implementation steps remain.
- Type consistency: Registry and schema module paths are fixed and shared by all tasks.
