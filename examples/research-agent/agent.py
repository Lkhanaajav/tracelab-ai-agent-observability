from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "sdk"))

from tracelab import TraceLabClient  # noqa: E402


JOB_TEXT = """
Founding Machine Learning Engineer role focused on production AI agents,
evaluation frameworks, model latency, browser automation, tool use, and
developer-facing infrastructure.
"""

PROJECTS = [
    {
        "name": "TraceLab",
        "evidence": [
            "AI agent observability dashboard",
            "tool-call correctness scoring",
            "latency and cost regression checks",
            "CI-ready eval gates",
        ],
    },
    {
        "name": "ApplyPilot",
        "evidence": ["resume tailoring", "job matching", "application tracking"],
    },
    {
        "name": "BEV Dashboard",
        "evidence": ["robotics perception", "3.0 ms inference", "semantic segmentation"],
    },
]


def sleep_ms(min_ms: int, max_ms: int) -> int:
    latency = random.randint(min_ms, max_ms)
    time.sleep(latency / 1000)
    return latency


def extract_requirements(job_text: str) -> dict[str, list[str]]:
    return {
        "requirements": [
            "agent evaluation",
            "tool-use reliability",
            "latency optimization",
            "developer tooling",
            "production AI systems",
        ]
    }


def rank_evidence(projects: list[dict[str, object]], requirements: list[str]) -> dict[str, object]:
    scores = []
    for project in projects:
        evidence = " ".join(project["evidence"]).lower()
        score = sum(1 for requirement in requirements if any(word in evidence for word in requirement.split()))
        scores.append({"project": project["name"], "score": score, "evidence": project["evidence"]})
    scores.sort(key=lambda item: item["score"], reverse=True)
    return {"ranked": scores, "top_project": scores[0]["project"]}


def run_agent(mode: str, base_url: str) -> str:
    client = TraceLabClient(base_url)
    run = client.create_run("resume-fit-001", "research-agent", "deterministic-demo-agent")

    run.prompt(
        "task_prompt",
        "Choose the strongest portfolio project for a founding ML engineer role.",
        token_count=145,
    )

    req_latency = sleep_ms(120, 260)
    requirements = extract_requirements(JOB_TEXT)
    run.tool_call(
        "extract_requirements",
        {"job_text": JOB_TEXT.strip()},
        requirements,
        latency_ms=req_latency,
    )

    citations: list[str]
    if mode == "bad":
        bad_latency = sleep_ms(260, 420)
        run.tool_call(
            "portfolio_selector",
            {"projects": ["generic chatbot"]},
            {"top_project": "generic chatbot", "confidence": 0.37},
            latency_ms=bad_latency,
        )
        output = "Build a general chatbot because it is easy to demo."
        citations = []
        answer_score = 0.31
        tool_score = 0.5
        grounded_score = 0.15
        status = "failed"
    else:
        rank_latency = sleep_ms(180, 360)
        ranking = rank_evidence(PROJECTS, requirements["requirements"])
        run.tool_call(
            "rank_evidence",
            {"projects": PROJECTS, "requirements": requirements["requirements"]},
            ranking,
            latency_ms=rank_latency,
        )
        output = (
            "TraceLab is the strongest project because it demonstrates agent "
            "evaluation, trace observability, tool-call correctness, and latency/cost "
            "regression checks for production AI systems. [requirements] [project-evidence]"
        )
        citations = ["requirements", "project-evidence"]
        answer_score = 0.95
        tool_score = 1.0
        grounded_score = 0.9
        status = "passed"

    output_latency = sleep_ms(280, 520)
    token_count = 640 if mode == "good" else 410
    run.output(output, citations=citations, latency_ms=output_latency, token_count=token_count)

    total_estimated_cost = 0.006 if mode == "good" else 0.004
    run.eval("answer_quality", answer_score, answer_score >= 0.75, "Measures whether the recommendation addresses the job signal.")
    run.eval("required_tool_used", tool_score, tool_score == 1.0, "Checks whether extract_requirements and rank_evidence were both used.")
    run.eval("groundedness", grounded_score, grounded_score >= 0.7, "Checks whether the answer is supported by project evidence and citations.")
    run.eval("contains_required_citations", 1.0 if citations else 0.0, len(citations) >= 2, "Requires two citations for evidence-backed output.")
    run.eval("cost_under_budget", 1.0, True, "Estimated cost stays under the configured budget.")
    run.finish(status=status, estimated_cost_usd=total_estimated_cost)
    return run.id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TraceLab research-agent demo.")
    parser.add_argument("--mode", choices=["good", "bad"], default="good")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    run_id = run_agent(args.mode, args.base_url)
    print(f"created {run_id}")


if __name__ == "__main__":
    main()

