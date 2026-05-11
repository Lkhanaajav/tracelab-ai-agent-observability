from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "tracelab.sqlite3"

app = FastAPI(title="TraceLab API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventIn(BaseModel):
    event_type: str
    name: str
    input_json: dict[str, Any] = {}
    output_json: dict[str, Any] = {}
    latency_ms: int = 0
    token_count: int = 0


class RunIn(BaseModel):
    task_id: str
    agent_name: str
    model: str
    status: str = "running"
    final_output: str = ""


class RunUpdate(BaseModel):
    status: str
    final_output: str
    total_latency_ms: int
    total_tokens: int
    estimated_cost_usd: float


class EvalIn(BaseModel):
    metric_name: str
    score: float
    passed: bool
    explanation: str


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ("input_json", "output_json", "eval_config"):
        if key in item and isinstance(item[key], str):
            item[key] = json.loads(item[key])
    return item


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              input TEXT NOT NULL,
              expected_behavior TEXT NOT NULL,
              eval_config TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY,
              task_id TEXT NOT NULL,
              agent_name TEXT NOT NULL,
              model TEXT NOT NULL,
              status TEXT NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT NOT NULL,
              total_latency_ms INTEGER NOT NULL,
              total_tokens INTEGER NOT NULL,
              estimated_cost_usd REAL NOT NULL,
              final_output TEXT NOT NULL,
              FOREIGN KEY(task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS trace_events (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              sequence_index INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              name TEXT NOT NULL,
              input_json TEXT NOT NULL,
              output_json TEXT NOT NULL,
              latency_ms INTEGER NOT NULL,
              token_count INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS eval_results (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              metric_name TEXT NOT NULL,
              score REAL NOT NULL,
              passed INTEGER NOT NULL,
              explanation TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(id)
            );
            """
        )


def seed_db(force: bool = False) -> None:
    init_db()
    with connect() as conn:
        if not force:
            existing = conn.execute("SELECT COUNT(*) AS count FROM runs").fetchone()
            if existing and existing["count"] > 0:
                return

        conn.executescript(
            "DELETE FROM eval_results; DELETE FROM trace_events; DELETE FROM runs; DELETE FROM tasks;"
        )

        tasks = [
            (
                "resume-fit-001",
                "Match portfolio project to AI observability role",
                "Given a founding ML engineer job description, identify which portfolio project best demonstrates agent reliability, evals, and production AI systems.",
                "Answer should recommend TraceLab and cite observability, evaluation, latency, and tool-use correctness evidence.",
                {
                    "required_tools": ["extract_requirements", "rank_evidence"],
                    "expected_facts": ["TraceLab", "observability", "tool-call correctness"],
                    "max_latency_ms": 5000,
                    "max_cost_usd": 0.02,
                    "required_citations": 2,
                },
            ),
            (
                "rag-grounding-002",
                "Answer from mini corpus with citations",
                "Answer a technical question using only the provided corpus and include source citations.",
                "Answer must stay grounded in retrieved documents and include at least two citations.",
                {
                    "required_tools": ["retrieve_documents"],
                    "expected_facts": ["grounded answer", "citations"],
                    "max_latency_ms": 4500,
                    "max_cost_usd": 0.015,
                    "required_citations": 2,
                },
            ),
            (
                "tool-args-003",
                "Validate tool argument selection",
                "Use the calculator and schema validator tools to produce a JSON answer.",
                "Agent must call the correct tools with valid arguments and return schema-valid JSON.",
                {
                    "required_tools": ["calculator", "schema_validator"],
                    "expected_facts": ["valid JSON"],
                    "max_latency_ms": 3000,
                    "max_cost_usd": 0.01,
                    "required_citations": 0,
                },
            ),
        ]

        conn.executemany(
            """
            INSERT INTO tasks (id, name, input, expected_behavior, eval_config)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(task[0], task[1], task[2], task[3], json.dumps(task[4])) for task in tasks],
        )

        def add_run(
            run_id: str,
            task_id: str,
            status: str,
            latency: int,
            tokens: int,
            cost: float,
            output: str,
            events: list[dict[str, Any]],
            evals: list[tuple[str, float, bool, str]],
        ) -> None:
            conn.execute(
                """
                INSERT INTO runs
                (id, task_id, agent_name, model, status, started_at, ended_at,
                 total_latency_ms, total_tokens, estimated_cost_usd, final_output)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_id,
                    "research-agent",
                    "gpt-4.1-mini",
                    status,
                    "2026-05-10T20:46:00Z",
                    "2026-05-10T20:46:04Z",
                    latency,
                    tokens,
                    cost,
                    output,
                ),
            )
            for index, event in enumerate(events, start=1):
                conn.execute(
                    """
                    INSERT INTO trace_events
                    (id, run_id, sequence_index, event_type, name, input_json,
                     output_json, latency_ms, token_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        run_id,
                        index,
                        event["event_type"],
                        event["name"],
                        json.dumps(event.get("input_json", {})),
                        json.dumps(event.get("output_json", {})),
                        event.get("latency_ms", 0),
                        event.get("token_count", 0),
                        f"2026-05-10T20:46:0{index}Z",
                    ),
                )
            for metric, score, passed, explanation in evals:
                conn.execute(
                    """
                    INSERT INTO eval_results
                    (id, run_id, metric_name, score, passed, explanation)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), run_id, metric, score, int(passed), explanation),
                )

        add_run(
            "run-good-001",
            "resume-fit-001",
            "passed",
            3180,
            1820,
            0.012,
            "TraceLab is the strongest project for AI observability roles because it demonstrates traces, evals, latency/cost analytics, and tool-call correctness with CI gates. [project-spec] [job-trends]",
            [
                {
                    "event_type": "prompt",
                    "name": "system_prompt",
                    "input_json": {"role": "research agent"},
                    "output_json": {"prompt_tokens": 420},
                    "latency_ms": 18,
                    "token_count": 420,
                },
                {
                    "event_type": "tool_call",
                    "name": "extract_requirements",
                    "input_json": {"job": "Founding ML engineer, agent reliability"},
                    "output_json": {"requirements": ["agent evals", "latency", "tool use"]},
                    "latency_ms": 280,
                    "token_count": 0,
                },
                {
                    "event_type": "tool_call",
                    "name": "rank_evidence",
                    "input_json": {"projects": ["TraceLab", "ApplyPilot", "BEV Dashboard"]},
                    "output_json": {"top_project": "TraceLab", "confidence": 0.93},
                    "latency_ms": 420,
                    "token_count": 0,
                },
                {
                    "event_type": "model_output",
                    "name": "final_answer",
                    "input_json": {},
                    "output_json": {"citations": ["project-spec", "job-trends"]},
                    "latency_ms": 2462,
                    "token_count": 1400,
                },
            ],
            [
                ("answer_quality", 0.94, True, "Answer directly recommends TraceLab and explains why."),
                ("required_tool_used", 1.0, True, "Both required tools were called."),
                ("groundedness", 0.88, True, "Claims are tied to project and job-trend evidence."),
                ("latency_under_budget", 1.0, True, "3180 ms is under 5000 ms."),
                ("cost_under_budget", 1.0, True, "$0.012 is under the $0.02 budget."),
            ],
        )

        add_run(
            "run-bad-001",
            "resume-fit-001",
            "failed",
            6420,
            3910,
            0.031,
            "Build a general chatbot portfolio app. It can answer questions and looks modern.",
            [
                {
                    "event_type": "prompt",
                    "name": "system_prompt",
                    "input_json": {"role": "research agent"},
                    "output_json": {"prompt_tokens": 420},
                    "latency_ms": 20,
                    "token_count": 420,
                },
                {
                    "event_type": "tool_call",
                    "name": "extract_requirements",
                    "input_json": {"job": "Founding ML engineer, agent reliability"},
                    "output_json": {"requirements": ["agent evals", "latency", "tool use"]},
                    "latency_ms": 310,
                    "token_count": 0,
                },
                {
                    "event_type": "tool_call",
                    "name": "portfolio_selector",
                    "input_json": {"projects": ["chatbot"]},
                    "output_json": {"top_project": "chatbot", "confidence": 0.41},
                    "latency_ms": 590,
                    "token_count": 0,
                },
                {
                    "event_type": "model_output",
                    "name": "final_answer",
                    "input_json": {},
                    "output_json": {"citations": []},
                    "latency_ms": 5500,
                    "token_count": 3490,
                },
            ],
            [
                ("answer_quality", 0.36, False, "Answer is generic and misses the observability angle."),
                ("required_tool_used", 0.5, False, "rank_evidence was not called."),
                ("groundedness", 0.18, False, "No citations or supporting evidence."),
                ("latency_under_budget", 0.0, False, "6420 ms exceeds the 5000 ms budget."),
                ("cost_under_budget", 0.0, False, "$0.031 exceeds the $0.02 budget."),
            ],
        )

        add_run(
            "run-rag-002",
            "rag-grounding-002",
            "passed",
            2875,
            1650,
            0.011,
            "The answer is grounded in retrieved corpus passages and includes citations to both selected documents. [doc-a] [doc-c]",
            [
                {
                    "event_type": "tool_call",
                    "name": "retrieve_documents",
                    "input_json": {"query": "agent evaluation groundedness"},
                    "output_json": {"documents": ["doc-a", "doc-c"]},
                    "latency_ms": 540,
                    "token_count": 0,
                },
                {
                    "event_type": "model_output",
                    "name": "final_answer",
                    "input_json": {},
                    "output_json": {"citations": ["doc-a", "doc-c"]},
                    "latency_ms": 2335,
                    "token_count": 1650,
                },
            ],
            [
                ("contains_required_citations", 1.0, True, "Two citations were present."),
                ("groundedness", 0.91, True, "Answer stays inside retrieved document claims."),
                ("latency_under_budget", 1.0, True, "2875 ms is under 4500 ms."),
            ],
        )


@app.on_event("startup")
def startup() -> None:
    seed_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/seed")
def reseed() -> dict[str, str]:
    seed_db(force=True)
    return {"status": "seeded"}


@app.get("/tasks")
def tasks() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [row_to_dict(row) for row in rows]


@app.get("/runs")
def runs() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.*, t.name AS task_name,
              AVG(e.score) AS average_score,
              SUM(CASE WHEN e.passed = 0 THEN 1 ELSE 0 END) AS failed_metrics
            FROM runs r
            JOIN tasks t ON t.id = r.task_id
            LEFT JOIN eval_results e ON e.run_id = r.id
            GROUP BY r.id
            ORDER BY r.started_at DESC, r.id
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


@app.get("/runs/{run_id}")
def run_detail(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        run = conn.execute(
            """
            SELECT r.*, t.name AS task_name, t.input AS task_input,
              t.expected_behavior, t.eval_config
            FROM runs r
            JOIN tasks t ON t.id = r.task_id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        events = conn.execute(
            "SELECT * FROM trace_events WHERE run_id = ? ORDER BY sequence_index",
            (run_id,),
        ).fetchall()
        evals = conn.execute(
            "SELECT * FROM eval_results WHERE run_id = ? ORDER BY metric_name",
            (run_id,),
        ).fetchall()
    return {
        **row_to_dict(run),
        "events": [row_to_dict(row) for row in events],
        "evals": [row_to_dict(row) for row in evals],
    }


@app.post("/runs")
def create_run(run: RunIn) -> dict[str, str]:
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    with connect() as conn:
        task = conn.execute("SELECT id FROM tasks WHERE id = ?", (run.task_id,)).fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        conn.execute(
            """
            INSERT INTO runs
            (id, task_id, agent_name, model, status, started_at, ended_at,
             total_latency_ms, total_tokens, estimated_cost_usd, final_output)
            VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0, 0, 0, ?)
            """,
            (run_id, run.task_id, run.agent_name, run.model, run.status, run.final_output),
        )
    return {"id": run_id}


@app.patch("/runs/{run_id}")
def update_run(run_id: str, update: RunUpdate) -> dict[str, str]:
    with connect() as conn:
        existing = conn.execute("SELECT id FROM runs WHERE id = ?", (run_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Run not found")
        conn.execute(
            """
            UPDATE runs
            SET status = ?, final_output = ?, total_latency_ms = ?, total_tokens = ?,
                estimated_cost_usd = ?, ended_at = datetime('now')
            WHERE id = ?
            """,
            (
                update.status,
                update.final_output,
                update.total_latency_ms,
                update.total_tokens,
                update.estimated_cost_usd,
                run_id,
            ),
        )
    return {"id": run_id}


@app.post("/runs/{run_id}/events")
def add_event(run_id: str, event: EventIn) -> dict[str, str]:
    with connect() as conn:
        run = conn.execute("SELECT id FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        next_index = conn.execute(
            "SELECT COALESCE(MAX(sequence_index), 0) + 1 AS next_index FROM trace_events WHERE run_id = ?",
            (run_id,),
        ).fetchone()["next_index"]
        event_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO trace_events
            (id, run_id, sequence_index, event_type, name, input_json, output_json,
             latency_ms, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                event_id,
                run_id,
                next_index,
                event.event_type,
                event.name,
                json.dumps(event.input_json),
                json.dumps(event.output_json),
                event.latency_ms,
                event.token_count,
            ),
        )
    return {"id": event_id}


@app.post("/runs/{run_id}/evals")
def add_eval(run_id: str, result: EvalIn) -> dict[str, str]:
    with connect() as conn:
        run = conn.execute("SELECT id FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        eval_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO eval_results
            (id, run_id, metric_name, score, passed, explanation)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                eval_id,
                run_id,
                result.metric_name,
                result.score,
                int(result.passed),
                result.explanation,
            ),
        )
    return {"id": eval_id}


@app.get("/regression/{task_id}")
def regression(task_id: str) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.*, AVG(e.score) AS average_score
            FROM runs r
            LEFT JOIN eval_results e ON e.run_id = r.id
            WHERE r.task_id = ?
            GROUP BY r.id
            ORDER BY r.started_at DESC, r.id
            LIMIT 2
            """,
            (task_id,),
        ).fetchall()
    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Need two runs for regression comparison")
    latest, baseline = [row_to_dict(row) for row in rows]
    return {
        "task_id": task_id,
        "latest": latest,
        "baseline": baseline,
        "delta": {
            "score": round((latest["average_score"] or 0) - (baseline["average_score"] or 0), 3),
            "latency_ms": latest["total_latency_ms"] - baseline["total_latency_ms"],
            "cost_usd": round(latest["estimated_cost_usd"] - baseline["estimated_cost_usd"], 4),
            "tokens": latest["total_tokens"] - baseline["total_tokens"],
        },
    }
