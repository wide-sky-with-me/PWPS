# Phase 7 Audit Repair Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert audit issues into repair targets and re-enter the Guided field-confirmation workflow for actionable conflicts.

**Architecture:** Keep deterministic audit rules in `audit/engine.py` and repair-target mapping in `audit/repair.py`. Persist derived repair targets in `WorkflowState`. Auto Draft records repair targets for review; Guided Draft re-enters hard-conflict and completeness targets until the user submits a repaired value.

**Tech Stack:** Python 3.12, Pydantic v2, pytest.

---

### Task 1: Audit Evidence Strength and Repair Mapping

**Files:**
- Modify: `apps/api/src/pwps_agent_api/audit/engine.py`
- Create: `apps/api/src/pwps_agent_api/audit/repair.py`
- Modify: `apps/api/src/pwps_agent_api/schemas/models.py`
- Create: `apps/api/tests/test_audit_repair.py`

- [ ] Add failing tests for low-credibility evidence downgrade and deduplicated repair targets.
- [ ] Run `uv run pytest tests/test_audit_repair.py -q` and confirm failure because repair mapping is missing.
- [ ] Pass evidence store into deterministic audit and add low-credibility evidence issues.
- [ ] Map audit issues with `repair_target` into `FieldTarget` values and persist them on `WorkflowState`.

### Task 2: Guided Repair Re-entry

**Files:**
- Modify: `apps/api/src/pwps_agent_api/workflow/auto.py`
- Modify: `apps/api/src/pwps_agent_api/workflow/guided.py`
- Modify: `apps/api/src/pwps_agent_api/skills/candidate_generation.py`
- Modify: `apps/api/tests/test_guided_run_api.py`

- [ ] Add failing API integration test for `GMAW + J422`, Guided repair re-entry, corrected recommendation, and successful completion.
- [ ] Record repair targets after Auto audit.
- [ ] Re-enter Guided confirmation for actionable hard and completeness repair targets.
- [ ] Regenerate candidates for `needs_repair` fields.

### Task 3: Output and Verification

**Files:**
- Modify: `apps/api/src/pwps_agent_api/output/builder.py`
- Modify: `README.md`

- [ ] Include repair targets in the risk report.
- [ ] Update README current-phase status.
- [ ] Run backend tests, Ruff, and mypy.

---

## Self-Review

- Spec coverage: Detects the documented GMAW/J422 hard conflict, keeps provided-only audit behavior, downgrades low-evidence high-risk fields, generates repair targets, and re-enters Guided confirmation.
- Scope: Does not add an unconstrained planner or silently mutate field values.
- Boundary check: AuditEngine reports issues; repair mapping creates targets; workflow controls re-entry; user decisions still commit values.
