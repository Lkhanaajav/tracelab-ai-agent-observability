from __future__ import annotations

import time
import urllib.error
import urllib.request
import json
from dataclasses import dataclass, field
from typing import Any


def _request(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"TraceLab API error {exc.code}: {detail}") from exc


@dataclass
class TraceRun:
    client: "TraceLabClient"
    id: str
    task_id: str
    agent_name: str
    model: str
    started_at: float = field(default_factory=time.perf_counter)
    total_tokens: int = 0
    final_output: str = ""

    def event(
        self,
        event_type: str,
        name: str,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        latency_ms: int = 0,
        token_count: int = 0,
    ) -> None:
        self.total_tokens += token_count
        self.client.add_event(
            self.id,
            {
                "event_type": event_type,
                "name": name,
                "input_json": input_json or {},
                "output_json": output_json or {},
                "latency_ms": latency_ms,
                "token_count": token_count,
            },
        )

    def prompt(self, name: str, text: str, token_count: int = 0) -> None:
        self.event(
            "prompt",
            name,
            input_json={"text": text},
            output_json={"estimated_tokens": token_count},
            token_count=token_count,
        )

    def tool_call(
        self,
        name: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any],
        latency_ms: int,
    ) -> None:
        self.event(
            "tool_call",
            name,
            input_json=input_json,
            output_json=output_json,
            latency_ms=latency_ms,
        )

    def output(self, text: str, citations: list[str], latency_ms: int, token_count: int) -> None:
        self.final_output = text
        self.event(
            "model_output",
            "final_answer",
            output_json={"text": text, "citations": citations},
            latency_ms=latency_ms,
            token_count=token_count,
        )

    def eval(self, metric_name: str, score: float, passed: bool, explanation: str) -> None:
        self.client.add_eval(
            self.id,
            {
                "metric_name": metric_name,
                "score": score,
                "passed": passed,
                "explanation": explanation,
            },
        )

    def finish(self, status: str, estimated_cost_usd: float) -> None:
        total_latency_ms = int((time.perf_counter() - self.started_at) * 1000)
        self.client.update_run(
            self.id,
            {
                "status": status,
                "final_output": self.final_output,
                "total_latency_ms": total_latency_ms,
                "total_tokens": self.total_tokens,
                "estimated_cost_usd": estimated_cost_usd,
            },
        )


class TraceLabClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def create_run(self, task_id: str, agent_name: str, model: str) -> TraceRun:
        response = _request(
            "POST",
            f"{self.base_url}/runs",
            {"task_id": task_id, "agent_name": agent_name, "model": model},
        )
        return TraceRun(self, response["id"], task_id, agent_name, model)

    def add_event(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _request("POST", f"{self.base_url}/runs/{run_id}/events", payload)

    def add_eval(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _request("POST", f"{self.base_url}/runs/{run_id}/evals", payload)

    def update_run(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _request("PATCH", f"{self.base_url}/runs/{run_id}", payload)

