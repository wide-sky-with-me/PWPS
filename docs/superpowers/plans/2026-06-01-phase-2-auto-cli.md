# Phase 2 Auto CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the MVP Auto Draft CLI loop that converts the sample pWPS request into structured JSON outputs.

**Architecture:** Use LangGraph `StateGraph` for deterministic node orchestration. Keep LLM-facing behavior behind mock Skill modules with Pydantic-compatible structured outputs, keep model-prior retrieval in a Knowledge module, keep confirmation in `VirtualDecisionActor`, keep audit deterministic, and keep final JSON file writing in an Output module.

**Tech Stack:** Python 3.12+, Pydantic v2, LangGraph 1.x, pytest, ruff, mypy, argparse.

---

### Task 1: Auto Draft Service and Outputs

**Files:**
- Create: `apps/api/tests/test_auto_draft_workflow.py`
- Create: `apps/api/src/pwps_agent_api/workflow/auto.py`
- Create: `apps/api/src/pwps_agent_api/skills/requirement_understanding.py`
- Create: `apps/api/src/pwps_agent_api/skills/candidate_generation.py`
- Create: `apps/api/src/pwps_agent_api/knowledge/model_prior.py`
- Create: `apps/api/src/pwps_agent_api/actors/virtual.py`
- Create: `apps/api/src/pwps_agent_api/audit/engine.py`
- Create: `apps/api/src/pwps_agent_api/output/builder.py`

- [ ] **Step 1: Write failing workflow tests**

Tests must call `run_auto_draft("Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案", output_dir)` and assert that `pwps.json`, `field_report.json`, `risk_report.json`, and `discussion_trace.json` are written.

- [ ] **Step 2: Run tests to verify missing workflow fails**

Run: `cd apps/api && uv run pytest tests/test_auto_draft_workflow.py -q`
Expected: FAIL because `pwps_agent_api.workflow.auto` does not exist yet.

- [ ] **Step 3: Implement deterministic workflow modules**

Nodes:

```text
normalize_input
understand_requirement
select_mode
build_confirmation_queue
confirm_target_subgraph
global_audit
finalize_output
```

MVP behavior:

- Extract provided fields from the documented sample input.
- Build the default field registry queue.
- Generate deterministic model-prior candidates for missing MVP fields.
- Use `VirtualDecisionActor` to accept recommended candidates only from the candidate bundle.
- Leave meta fields empty because they are `PROVIDED_ONLY`.
- Add deterministic audit issues for high-risk auto-confirmed fields and weak model-prior evidence.
- Write the four required JSON outputs.

- [ ] **Step 4: Run workflow tests to verify pass**

Run: `cd apps/api && uv run pytest tests/test_auto_draft_workflow.py -q`
Expected: PASS.

### Task 2: CLI Entrypoint

**Files:**
- Create: `apps/api/tests/test_auto_draft_cli.py`
- Create: `apps/api/src/pwps_agent_api/cli/__init__.py`
- Create: `apps/api/src/pwps_agent_api/cli/auto_draft.py`

- [ ] **Step 1: Write failing CLI test**

Test must run:

```bash
uv run python -m pwps_agent_api.cli.auto_draft \
  --input "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案" \
  --output-dir <tmpdir>
```

and assert exit code 0 plus the four output files.

- [ ] **Step 2: Run CLI test to verify missing CLI fails**

Run: `cd apps/api && uv run pytest tests/test_auto_draft_cli.py -q`
Expected: FAIL because the CLI module does not exist yet.

- [ ] **Step 3: Implement argparse CLI**

The CLI should call `run_auto_draft()` and print the output directory path as JSON.

- [ ] **Step 4: Run CLI test to verify pass**

Run: `cd apps/api && uv run pytest tests/test_auto_draft_cli.py -q`
Expected: PASS.

### Task 3: Verification

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `README.md`

- [ ] **Step 1: Add LangGraph dependency**

Add `langgraph>=1.0.0` to backend dependencies. This is required by `docs/workflow.md`, and current usage was checked against LangGraph 1.0 docs.

- [ ] **Step 2: Update README with Auto CLI command**

Document the CLI command and outputs.

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

- Spec coverage: Covers Phase 2 MVP requirements from `development_stages.md` and `workflow.md`: natural-language input, field extraction, fixed queue, simple knowledge/model prior, candidate generation, `VirtualDecisionActor`, simple audit, and the four required output files.
- Placeholder scan: No `TBD` or unspecified implementation steps remain.
- Type consistency: Workflow API is `run_auto_draft(raw_input: str, output_dir: Path) -> AutoDraftResult`.
