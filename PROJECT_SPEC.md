# TraceLab

AI Agent Evaluation and Observability Platform

## Goal

Build a polished portfolio project that proves production AI engineering ability: tracing, evaluation, latency/cost analysis, tool-call correctness, and CI-style quality gates for LLM agents.

This should look like a real developer tool, not a chatbot demo.

## One-Line Pitch

TraceLab lets developers run AI agents on real tasks, inspect every tool call, score the final output, and catch regressions in latency, cost, and correctness before shipping.

## Target Roles

- Machine Learning Engineer
- AI Engineer
- ML Systems Engineer
- Founding Engineer
- Backend Engineer, AI Infrastructure
- Forward Deployed Engineer, AI Systems
- Developer Tools Engineer

## Why This Project Is Strong

The market is moving from "build a chatbot" to "make agent systems reliable." Companies hiring AI engineers now care about:

- Agent reliability
- Evals and regression testing
- RAG faithfulness
- Tool-use correctness
- Latency and cost
- Debuggability
- Production monitoring

TraceLab hits all of those.

## Demo Story

A recruiter or engineer opens the project and sees:

1. A dashboard with several agent runs.
2. One run failed because the agent used the wrong tool argument.
3. The trace view shows each step: prompt, tool call, observation, latency, token cost.
4. The eval panel shows pass/fail metrics: final answer quality, citation support, tool correctness, cost budget, latency budget.
5. A regression page compares the latest run against a baseline.
6. The CLI exits nonzero if quality drops below the configured threshold.

The demo should make one thing obvious: this is an engineering system for AI reliability.

## MVP Scope

### Must Have

- Web dashboard for agent runs
- Trace timeline with step-by-step events
- Run detail page with prompts, tool calls, observations, and outputs
- Metrics: latency, token usage, estimated cost, tool-call count
- Eval scoring:
  - final answer pass/fail
  - tool-call correctness
  - groundedness/citation score
  - latency budget
  - cost budget
- Dataset/task runner with at least 10 sample tasks
- CLI command to run evals locally
- Baseline comparison across runs
- SQLite or Postgres persistence
- Clean README with screenshots/GIF

### Nice To Have

- OpenTelemetry-style trace export
- RAG-specific eval mode
- Agent replay
- Failure clustering
- GitHub Actions example
- Multiple model/provider comparison
- Hosted demo with seed data

## Concrete MVP Use Case

Build around a small "research assistant agent" because it demonstrates tool use without needing a huge external system.

The agent gets tasks like:

- "Find which resume project best fits a robotics software role."
- "Summarize a job description and extract must-have requirements."
- "Answer a question from a mini-document corpus with citations."
- "Use a calculator/search/tool and return a structured answer."

TraceLab captures:

- what the agent planned
- which tool it called
- what the tool returned
- how long each step took
- whether the final answer was supported by evidence

## Architecture

```text
tracelab/
  apps/
    web/                 Next.js dashboard
    api/                 FastAPI backend
  packages/
    sdk/                 Python tracing SDK
    evals/               scoring and task runner
  examples/
    research-agent/      demo agent instrumented with TraceLab
  data/
    seed/                sample tasks and documents
```

## Recommended Stack

Frontend:

- Next.js
- TypeScript
- Tailwind CSS
- Recharts or Tremor for charts

Backend:

- FastAPI
- Python
- SQLModel or SQLAlchemy
- SQLite for local demo, Postgres-ready schema

Agent/Evals:

- Python SDK
- OpenAI API compatible interface
- Optional local/mock model mode for demo reliability
- RAGAS-inspired groundedness scoring, but implement lightweight custom evals first

Testing:

- Pytest for backend/evals
- Playwright for UI smoke tests
- GitHub Actions workflow

## Data Model

Core tables:

- `runs`
  - id
  - task_id
  - agent_name
  - model
  - status
  - started_at
  - ended_at
  - total_latency_ms
  - total_tokens
  - estimated_cost_usd
  - final_output
- `trace_events`
  - id
  - run_id
  - sequence_index
  - event_type: prompt, tool_call, tool_result, model_output, error
  - name
  - input_json
  - output_json
  - latency_ms
  - token_count
  - created_at
- `eval_results`
  - id
  - run_id
  - metric_name
  - score
  - passed
  - explanation
- `tasks`
  - id
  - name
  - input
  - expected_behavior
  - eval_config

## Dashboard Pages

### Runs

Table of recent runs:

- status
- task
- model
- total score
- latency
- cost
- failure reason

### Run Detail

Primary page:

- top summary cards
- trace timeline
- event detail inspector
- final answer
- eval scores
- failure explanation

### Regression

Compare latest run vs baseline:

- total score delta
- latency delta
- cost delta
- failed metrics
- changed tool behavior

### Tasks

List evaluation tasks with:

- prompt/input
- expected behavior
- eval criteria
- latest pass/fail

## Evaluation Metrics

Start with deterministic metrics:

- `latency_under_budget`
- `cost_under_budget`
- `required_tool_used`
- `forbidden_tool_not_used`
- `json_schema_valid`
- `contains_required_citations`
- `answer_contains_expected_facts`

Then add LLM-as-judge metrics:

- `answer_quality`
- `groundedness`
- `instruction_following`
- `irrelevant_content`

## Build Phases

### Phase 1: Skeleton

- Create repo structure
- FastAPI backend
- SQLite schema
- Seed data
- Next.js dashboard shell

### Phase 2: Tracing SDK

- Python context manager for runs
- `trace_event()` helper
- store tool call inputs/outputs
- local example agent emits trace data

### Phase 3: Evals

- deterministic eval runner
- task config format
- baseline comparison
- CLI command: `tracelab eval examples/research-agent/tasks.yaml`

### Phase 4: Dashboard Polish

- run list
- run detail timeline
- score cards
- regression comparison
- screenshots for README

### Phase 5: Portfolio Packaging

- README with architecture diagram
- demo GIF
- resume bullets
- deploy backend/frontend or record a clean walkthrough
- write a short technical blog post

## Portfolio README Structure

1. What TraceLab does
2. Why agent observability matters
3. Screenshots/GIF
4. Architecture
5. Eval metrics
6. Example trace
7. Running locally
8. Running evals in CI
9. Design tradeoffs
10. Future work

## Resume Bullets

Use after completion:

- Built TraceLab, an AI agent observability and evaluation platform with trace replay, tool-call correctness scoring, latency/cost analytics, and CI-ready quality gates.
- Implemented a Python tracing SDK and FastAPI backend to capture model prompts, tool calls, observations, token usage, latency, and evaluation results across agent runs.
- Designed deterministic and LLM-as-judge eval pipelines for groundedness, instruction following, schema validity, tool-use correctness, and regression detection.
- Built a Next.js dashboard for inspecting agent traces, comparing baseline vs latest runs, and diagnosing quality, cost, and latency regressions.

## GitHub Topics

- ai-agents
- llm-evaluation
- llm-observability
- rag
- mlops
- fastapi
- nextjs
- openai
- developer-tools
- machine-learning

## What Not To Do

- Do not make this just a chat UI.
- Do not skip evals.
- Do not hide the backend behind mock data only.
- Do not make the dashboard decorative instead of diagnostic.
- Do not overbuild multi-provider support before the core trace/eval loop works.

## Success Criteria

The project is resume-ready when:

- A user can run an example agent and see a trace appear in the dashboard.
- At least 10 tasks run through the eval engine.
- At least 5 metrics are calculated per run.
- A regression comparison catches a deliberately worse run.
- The README has screenshots and a clear architecture diagram.
- Tests run in CI.

