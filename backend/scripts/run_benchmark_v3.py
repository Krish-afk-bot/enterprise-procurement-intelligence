"""Run the 120-question benchmark and write per-question + aggregate results.

    python scripts/run_benchmark_v3.py --top-k 10
    python scripts/run_benchmark_v3.py --limit 10 --out var/benchmark-smoke

Results are written even when individual questions fail, so a partial run can be
inspected instead of lost. The aggregate never treats a missing metric as a zero.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.config.container import get_container  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import dispose_engine, session_scope  # noqa: E402
from app.evaluation.benchmark import load_benchmark_dataset  # noqa: E402
from app.evaluation.benchmark_runner import BenchmarkRunner  # noqa: E402
from app.security.rbac import Principal  # noqa: E402

PROJECT_ROOT = ROOT.parent


def build_principal(user: User) -> Principal:
    return Principal(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name or "",
    )


def write_report(report: dict[str, Any], directory: Path) -> Path:
    run = report["run"]
    lines = [
        f"# Benchmark run — {run['started_at']}",
        "",
        f"- Questions: {run['question_count']}",
        f"- Strategy: {run.get('strategy') or 'pipeline default'} (top_k={run['top_k']})",
        f"- Model: {run.get('llm_model')} at {run.get('llm_endpoint')}",
        f"- Embeddings: {run.get('embedding_model')}; reranker: {run.get('reranker_enabled')}",
        f"- Generation modes: {json.dumps(run.get('generation_modes'))}",
        f"- Duration: {run.get('duration_seconds')} s",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value | n |",
        "| --- | --- | --- |",
        f"| Recall@5 | {report['retrieval']['recall_at_5']} | {report['retrieval']['questions']} |",
        f"| Recall@10 | {report['retrieval']['recall_at_10']} | {report['retrieval']['questions']} |",
        f"| MRR | {report['retrieval']['mrr']} | {report['retrieval']['questions']} |",
        f"| nDCG@10 | {report['retrieval']['ndcg_at_10']} | {report['retrieval']['questions']} |",
        f"| Answer correctness | {(report['answer']['correct'] or {}).get('rate')} | {report['answer']['questions']} |",
        f"| Citation precision | {report['citation']['mean_precision']} | {report['citation']['questions']} |",
        f"| Citation recall | {report['citation']['mean_recall']} | {report['citation']['questions']} |",
        f"| Faithfulness | {report['faithfulness']['mean']} | {report['faithfulness']['questions']} |",
        f"| Unsupported claim rate | {report['faithfulness']['unsupported_claim_rate']} | {report['faithfulness']['questions']} |",
        f"| Correct refusal accuracy | {(report['refusal']['accuracy'] or {}).get('rate')} | {report['refusal']['questions']} |",
        f"| Refusal precision | {report['refusal']['precision']} | — |",
        f"| Refusal recall | {report['refusal']['recall']} | — |",
        f"| Temporal correctness | {(report['temporal']['correct'] or {}).get('rate')} | {report['temporal']['questions']} |",
        f"| Latency p50 / p95 (ms) | {report['latency_ms']['p50']} / {report['latency_ms']['p95']} | {report['latency_ms']['count']} |",
        f"| Prompt / completion tokens | {report['tokens']['prompt_total']} / {report['tokens']['completion_total']} | — |",
        "",
        "## By category",
        "",
        "| Category | Q | Answer correct | Recall@10 | Citation precision | Faithfulness | Refusal P/R | Temporal | p50 ms |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for category, item in report["by_category"].items():
        answer = (item["answer_correct"] or {}).get("rate")
        temporal = (item["temporal_correct"] or {}).get("rate")
        lines.append(
            f"| {category} | {item['questions']} | {answer} | {item['recall_at_10']} | "
            f"{item['citation_precision']} | {item['faithfulness']} | "
            f"{item['refusal_precision']}/{item['refusal_recall']} | {temporal} | {item['latency_p50_ms']} |"
        )
    lines += ["", "## Failure taxonomy", "", "| Label | Count |", "| --- | --- |"]
    for label, count in report["failure_taxonomy"].items():
        lines.append(f"| {label} | {count} |")

    failures = [row for row in report["rows"] if row.get("failure_label")]
    lines += ["", "## Failed-question analysis", ""]
    if not failures:
        lines.append("No question was labelled as a failure.")
    else:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in failures:
            grouped[row["failure_label"]].append(row)
        for label, rows in sorted(grouped.items()):
            lines.append(f"### {label} ({len(rows)})")
            lines.append("")
            for row in rows[:6]:
                detail = ""
                if row.get("facts_missing"):
                    detail = f" — missing facts: {row['facts_missing']}"
                lines.append(f"- `{row['id']}` {row['question']}{detail}")
            if len(rows) > 6:
                lines.append(f"- … and {len(rows) - 6} more")
            lines.append("")

    lines += [
        "",
        "## How to read this",
        "",
        "- Answer correctness uses literal fact containment; a correct paraphrase is scored as a miss.",
        "- Faithfulness is the pipeline's own grounding verdict, not an independent judge.",
        "- No label in the dataset has been human-adjudicated; `auto_verified` means the evidence quote was machine-checked.",
        "- Metrics with no applicable questions are `null`, never zero.",
        "",
    ]
    path = directory / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the 120-question benchmark")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--category", action="append", default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--dataset-dir", default=None, help="Directory containing questions.json")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM network calls, run extractive pipeline")
    args = parser.parse_args()

    settings = get_settings()
    if args.no_llm:
        settings.llm_base_url = ""
    dataset_path = Path(args.dataset_dir) if args.dataset_dir else (settings.evaluation_dir / "benchmark_v3")
    dataset = load_benchmark_dataset(dataset_path)
    out_dir = Path(args.out) if args.out else (
        PROJECT_ROOT / "data" / "evaluation" / "benchmark_v3" / "results" / "baseline"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.role == "admin").limit(1))).scalar_one_or_none()
    if user is None:
        print("No admin user found; cannot run the benchmark.", file=sys.stderr)
        return 2
    principal = build_principal(user)

    container = get_container()
    await container.startup()
    runner = BenchmarkRunner(container, settings)

    def progress(index: int, total: int, row: dict[str, Any]) -> None:
        if args.quiet:
            return
        status = row.get("failure_label") or ("refused" if row.get("refused") else row.get("status"))
        print(f"[{index}/{total}] {row['id']} {row['category']} -> {status}", flush=True)

    try:
        report = await runner.run(
            principal,
            dataset,
            top_k=args.top_k,
            strategy=args.strategy,
            categories=args.category,
            limit=args.limit,
            on_row=progress,
        )
    finally:
        await container.shutdown()
        await dispose_engine()

    rows = report.pop("rows")
    (out_dir / "rows.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary = {key: value for key, value in report.items()}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out_dir / "dataset_used.json").write_text(
        json.dumps(dataset.summary(), indent=2), encoding="utf-8"
    )
    report_path = write_report({**report, "rows": rows}, out_dir)
    print(json.dumps({key: report[key] for key in ("answer", "refusal", "faithfulness", "temporal")}, indent=2, default=str))
    print(f"wrote {out_dir} (report: {report_path.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
