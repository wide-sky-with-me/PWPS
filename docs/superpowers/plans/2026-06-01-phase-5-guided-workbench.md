# Phase 5 Guided Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the scaffold page with a responsive Guided Draft field-confirmation workbench backed by the existing API.

**Architecture:** Keep API calls and TypeScript response types in `lib/api.ts`. Use one client component for workflow state and interaction, and smaller presentational components for progress, field cards, evidence, risk, and final output. The frontend only displays backend candidates and submits user decisions; it never infers field values or publishability.

**Tech Stack:** Next.js App Router, React 19, TypeScript, CSS, lucide-react.

---

### Task 1: Typed API Client

**Files:**
- Create: `apps/web/lib/api.ts`

- [ ] Add typed helpers for create run, fetch run, fetch current decision, submit decision, and fetch outputs.

### Task 2: Guided Workbench

**Files:**
- Replace: `apps/web/app/page.tsx`
- Create: `apps/web/components/guided-workbench.tsx`

- [ ] Add task creation form with mode selection and natural-language input.
- [ ] Add desktop three-column workbench: progress rail, confirmation card, evidence/risk rail.
- [ ] Add mobile single-column layout with sticky submit action.
- [ ] Add final output preview when the run reaches `finished`.

### Task 3: Visual System and Verification

**Files:**
- Replace: `apps/web/app/globals.css`
- Modify: `apps/web/package.json`
- Modify: `README.md`

- [ ] Add restrained industrial/utilitarian styling with risk labels and evidence accordions.
- [ ] Add `lucide-react` for command icons.
- [ ] Run:

```bash
pnpm install
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web build
```

---

## Self-Review

- Spec coverage: Implements the Phase 5 task creation page, field confirmation workbench, evidence panel, risk panel, final output preview, desktop three-column layout, and mobile adaptation.
- Scope: Uses existing API without adding frontend inference logic.
- Type consistency: API response types match `docs/api_contract.md`.
