"""Run the labelled evaluation set through the API and print the metrics.

Results are stored by the API itself (`evaluation_runs` / `evaluation_results`),
so an interrupted run leaves its per-question rows behind and can be inspected or
repeated. Metrics that the dataset cannot support stay ``null``; they are never
reported as zero.

Usage:
    python scripts/run_retrieval_evaluation.py --experiments dense sparse hybrid
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

SUMMARY_KEYS = (
    "questions",
    "recall_at_5",
    "recall_at_10",
    "precision_at_5",
    "reciprocal_rank",
    "ndcg_at_10",
    "page_coverage",
    "keyword_coverage",
    "answer_correct",
    "refusal_correct",
    "citation_validity",
    "reference_f1",
    "latency_ms",
)


def clear_stale(client: httpx.Client, headers: dict[str, str]) -> None:
    """A run left in `running` by a killed client can never finish on its own."""
    payload = client.get("/evaluation/runs", params={"limit": 50}, headers=headers).json()
    items = payload.get("items", payload) if isinstance(payload, dict) else payload
    for run in items:
        if run.get("status") == "running":
            response = client.delete(f"/evaluation/runs/{run['id']}", headers=headers)
            print(f"deleted stale run {run['id']} ({run.get('experiment')}): {response.status_code}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the retrieval evaluation experiments")
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--email", default="admin@epi.local")
    parser.add_argument("--password", default="admin-local-password")
    parser.add_argument("--experiments", nargs="+", default=["dense", "sparse", "hybrid"])
    parser.add_argument("--max-questions", type=int, default=12)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--clear-stale", action="store_true")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=1800.0) as client:
        token = client.post(
            "/auth/login", json={"email": args.email, "password": args.password}
        )
        token.raise_for_status()
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}

        dataset = client.get("/evaluation/dataset", headers=headers)
        if dataset.status_code >= 400:
            print(f"dataset unavailable: {dataset.status_code} {dataset.text[:300]}", file=sys.stderr)
            return 2
        print("dataset:", json.dumps(dataset.json()))

        if args.clear_stale:
            clear_stale(client, headers)

        started = time.time()
        response = client.post(
            "/evaluation/runs",
            headers=headers,
            json={
                "experiments": args.experiments,
                "max_questions": args.max_questions,
                "top_k": args.top_k,
            },
        )
        elapsed = round(time.time() - started, 1)
        print(f"POST /evaluation/runs -> {response.status_code} in {elapsed}s")
        if response.status_code >= 400:
            print(response.text[:1000], file=sys.stderr)
            return 1

        for run in response.json():
            summary = run.get("summary") or {}
            print(
                json.dumps(
                    {
                        "run_id": run.get("id"),
                        "experiment": run.get("experiment"),
                        "status": run.get("status"),
                        "dataset": run.get("dataset_name"),
                        "label": summary.get("label"),
                        "metrics": {key: summary.get(key) for key in SUMMARY_KEYS},
                        "notes": summary.get("notes"),
                        "error": run.get("error_message"),
                    },
                    indent=2,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
