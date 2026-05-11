from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TraceLab example evals.")
    parser.add_argument("--mode", choices=["good", "bad"], default="good")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--min-score", type=float, default=0.75)
    parser.add_argument("--max-failed", type=int, default=0)
    args = parser.parse_args()

    agent = ROOT / "examples" / "research-agent" / "agent.py"
    result = subprocess.run(
        [sys.executable, str(agent), "--mode", args.mode, "--base-url", args.base_url],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    run_id = result.stdout.strip().split()[-1]
    with urllib.request.urlopen(f"{args.base_url.rstrip('/')}/runs/{run_id}", timeout=10) as response:
        detail = json.loads(response.read().decode("utf-8"))

    evals = detail["evals"]
    avg_score = sum(item["score"] for item in evals) / len(evals)
    failed = [item for item in evals if not item["passed"]]

    print("")
    print("TraceLab Eval Gate")
    print(f"run_id: {run_id}")
    print(f"status: {detail['status']}")
    print(f"average_score: {avg_score:.2%}")
    print(f"failed_metrics: {len(failed)}")
    print(f"latency_ms: {detail['total_latency_ms']}")
    print(f"estimated_cost_usd: ${detail['estimated_cost_usd']:.3f}")

    if failed:
        print("")
        print("Failed metrics:")
        for item in failed:
            print(f"- {item['metric_name']}: {item['score']:.2%} | {item['explanation']}")

    gate_passed = avg_score >= args.min_score and len(failed) <= args.max_failed
    print("")
    print(f"gate: {'PASS' if gate_passed else 'FAIL'}")
    raise SystemExit(0 if gate_passed else 1)


if __name__ == "__main__":
    main()
