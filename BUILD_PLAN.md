# TraceLab Build Plan

## Decision

Build TraceLab as the flagship portfolio project.

Default target: local-first developer tool with a polished web dashboard and a working CLI eval runner.

## MVP Implementation Order

### 1. Project Scaffold

Create:

```text
tracelab/
  README.md
  docker-compose.yml
  apps/
    api/
    web/
  packages/
    sdk/
    evals/
  examples/
    research-agent/
```

Use SQLite first. Add Postgres config later only if needed.

### 2. Backend

Build FastAPI endpoints:

- `GET /health`
- `GET /runs`
- `POST /runs`
- `GET /runs/{run_id}`
- `POST /runs/{run_id}/events`
- `POST /runs/{run_id}/evals`
- `GET /tasks`
- `POST /eval/run`

Use SQLModel unless the repo constraints push another ORM.

### 3. Python SDK

Core API:

```python
from tracelab import TraceLabClient

client = TraceLabClient(base_url="http://localhost:8000")

with client.run(task_id="resume-fit-001", agent_name="research-agent", model="gpt-4.1-mini") as run:
    run.prompt("Summarize this job description...")
    with run.tool_call("extract_requirements", input={"text": jd}) as event:
        event.result({"requirements": [...]})
    run.output("Final answer...")
```

### 4. Example Agent

Build a deterministic research-agent first:

- reads sample job descriptions and mini-documents
- calls local tools like `extract_requirements`, `retrieve_documents`, `rank_evidence`
- emits traces through the SDK
- can simulate good and bad runs

This avoids needing API keys for the demo.

### 5. Evals

Task config:

```yaml
id: resume-fit-001
input: "Which project best fits this job?"
expected_facts:
  - "TraceLab fits AI observability and eval roles"
required_tools:
  - "extract_requirements"
  - "rank_evidence"
max_latency_ms: 5000
max_cost_usd: 0.02
required_citations: 2
```

Implement deterministic metrics first:

- schema validity
- expected facts
- required tool use
- latency budget
- cost budget
- citation count

### 6. Web Dashboard

Pages:

- `/runs`
- `/runs/[id]`
- `/tasks`
- `/regression`

Run detail layout:

- header score summary
- timeline left column
- selected event inspector right column
- eval result cards
- final output panel

### 7. Regression Mode

Compare two runs of the same task:

- score delta
- latency delta
- cost delta
- tool-call diff
- newly failed metrics

### 8. Portfolio Polish

Add:

- screenshots
- seeded demo data
- architecture diagram
- README badges
- one-command local run
- CI workflow

## First Coding Sprint

Build these first:

1. `tracelab/apps/api` FastAPI app with SQLite models.
2. Seed script that creates sample tasks and runs.
3. `GET /runs` and `GET /runs/{id}`.
4. Basic Next.js dashboard showing the seeded runs.

Stop after dashboard can show real stored trace data.

## Non-Negotiables

- Keep screenshots and demo quality high.
- Make traces real persisted records, not hardcoded JSON in the frontend.
- Keep README written like a serious open-source devtool.
- Every major feature should map to a resume bullet.

