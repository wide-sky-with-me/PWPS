# pWPS Agent

pWPS Agent is a field-driven, evidence-backed workflow system for producing reviewable pWPS draft data. It does not generate a formal signable WPS, PQR, or WPQR.

## Repository Layout

```text
apps/
  api/      FastAPI backend managed by uv
  web/      Next.js frontend managed by pnpm
infra/      Local PostgreSQL and Redis services
docs/       Product, architecture, workflow, schema, and safety contracts
```

## Prerequisites

- `uv`
- `pnpm`
- Node.js LTS
- Python 3.12+
- Docker with Compose support

## Local Setup

Start infrastructure:

```bash
cd infra
docker compose up -d
```

Install and run the backend:

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run fastapi dev src/pwps_agent_api/main.py
```

Check the API:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Install and run the frontend:

```bash
pnpm install
pnpm --filter web dev
```

Open `http://localhost:3000`.

## Verification

Backend:

```bash
cd apps/api
uv run pytest
uv run ruff check .
uv run mypy .
```

Frontend:

```bash
pnpm --filter web typecheck
pnpm --filter web lint
```

Document ingestion (optional, requires `EMBEDDING_API_KEY` in `.env`):

```bash
cd apps/api
uv run python -m pwps_agent_api.cli.ingest --source data/knowledge_base/local_documents.json
```

## Auto Draft CLI

Run the current Phase 2 MVP loop:

```bash
cd apps/api
uv run python -m pwps_agent_api.cli.auto_draft \
  --input "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案" \
  --output-dir ./storage/demo-run
```

The CLI writes:

```text
pwps.json
field_report.json
evidence_report.json
risk_report.json
discussion_trace.json
render_payload.json
```

## Run API

Start the backend after applying database migrations or creating the local schema:

```bash
cd apps/api
uv run alembic upgrade head
uv run fastapi dev src/pwps_agent_api/main.py
```

Create an Auto Draft run:

```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"input":"Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案","mode":"auto","attachments":[]}'
```

Fetch persisted run data:

```bash
curl http://127.0.0.1:8000/api/runs/<run_id>
curl http://127.0.0.1:8000/api/runs/<run_id>/outputs
curl http://127.0.0.1:8000/api/runs/<run_id>/events
```

Run events are published to Redis using `REDIS_URL` and are also persisted in the run record as a durable fallback for `/events`.

Create a Guided Draft run by sending `"mode":"guided"`. Guided runs pause with `waiting_for_user`; retrieve and submit the current field-group decision with:

```bash
curl http://127.0.0.1:8000/api/runs/<run_id>/current-decision
curl -X POST http://127.0.0.1:8000/api/runs/<run_id>/decision \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","decision_type":"accept_recommended","selected_values":{},"comment":"accept"}'
```

## Current Phase

The project has completed Phase 0 through Phase 9 (evaluation, observability, security, deployment):

- All Phase 0-8 deliverables remain complete.
- All 8 required skills implemented with LLM + deterministic fallback.
- DecisionActor base class with VirtualDecisionActor and HumanDecisionActor.
- Auto/Guided workflows unified via shared `workflow/common.py`.
- File upload endpoint with security measures (type whitelist, size limit, isolated storage).
- All error codes from API contract implemented.
- Evidence report as independent output file.
- Dockerfiles for API and Web services.
- GitHub Actions CI/CD pipeline.
- 50 backend tests passing, ruff + mypy clean.

The web app exposes the Guided workbench at `http://127.0.0.1:3000`.

Next steps: populate Milvus with real welding standard documents, add frontend tests, and production deployment.
