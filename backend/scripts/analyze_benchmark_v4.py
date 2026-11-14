"""Recompute benchmark metrics from per-question rows and compare runs.

All runs are scored with the same functions in this file, including the locked
v3 baseline, so a comparison is not a comparison of two different definitions.
"""

from __future__ import annotations

import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "data" / "evaluation"
V4 = EVAL / "benchmark_v4"
BASE = EVAL / "benchmark_v3" / "results" / "baseline"


def load_rows(path: Path) -> list[dict[str, Any]]:
    file = path / "rows.jsonl"
    if not file.exists():
        return []
    return [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm_fact(value: str) -> str:
    text = (value or "").lower().replace("£", "").replace("$", "")
    text = re.sub(r"[\u2019\u2018]", "'", text)
    text = re.sub(r"[\u2013\u2014]", "-", text)
    text = re.sub(r"(?<=\d)[,\s](?=\d)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def facts_in(answer: str, facts: list[str]) -> tuple[int, list[str]]:
    haystack = norm_fact(answer)
    missing = [fact for fact in facts if norm_fact(fact) not in haystack]
    return len(facts) - len(missing), missing


def doc_key(value: str) -> str:
    """Retrieval returns file stems; labels use file names."""
    return Path(str(value)).stem.lower()


def recall_at(rows: list[dict[str, Any]], k: int) -> float | None:
    scored = [
        row
        for row in rows
        if row.get("expected_documents") and row.get("retrieved_documents") is not None
    ]
    if not scored:
        return None
    hits = 0
    for row in scored:
        top = [doc_key(doc) for doc in (row.get("retrieved_documents") or [])[:k]]
        if any(doc_key(doc) in top for doc in row["expected_documents"]):
            hits += 1
    return round(hits / len(scored), 4)


def mrr(rows: list[dict[str, Any]]) -> float | None:
    scored = [row for row in rows if row.get("expected_documents")]
    if not scored:
        return None
    total = 0.0
    for row in scored:
        docs = [doc_key(doc) for doc in (row.get("retrieved_documents") or [])]
        expected = {doc_key(doc) for doc in row["expected_documents"]}
        rank = next((i + 1 for i, doc in enumerate(docs) if doc in expected), None)
        total += 1 / rank if rank else 0.0
    return round(total / len(scored), 4)


def ndcg_at(rows: list[dict[str, Any]], k: int = 10) -> float | None:
    scored = [row for row in rows if row.get("expected_documents")]
    if not scored:
        return None
    total = 0.0
    for row in scored:
        expected = {doc_key(doc) for doc in row["expected_documents"]}
        docs = [doc_key(doc) for doc in (row.get("retrieved_documents") or [])][:k]
        gains = [1.0 if doc in expected else 0.0 for doc in docs]
        dcg = sum(gain / math.log2(i + 2) for i, gain in enumerate(gains))
        ideal = 1.0 if row["expected_documents"] else 0.0
        total += dcg / ideal if ideal else 0.0
    return round(total / len(scored), 4)


def wilson(successes: int, total: int) -> dict[str, float] | None:
    if not total:
        return None
    z = 1.96
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return {"rate": round(p, 4), "low": round(max(0, centre - margin), 4), "high": round(min(1, centre + margin), 4), "successes": successes, "total": total}


def refusal(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    for row in rows:
        refused = bool(row.get("refused"))
        expected = bool(row.get("expected_refusal"))
        if expected and refused:
            tp += 1
        elif expected and not refused:
            fn += 1
        elif not expected and refused:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "tp": tp, "fp_false_refusal": fp, "fn_false_answer": fn, "tn": tn,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "accuracy": wilson(tp + tn, len(rows)),
        "questions": len(rows),
    }


def answer_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if not row.get("expected_refusal") and row.get("expected_facts")]
    literal = sum(1 for row in answerable if row.get("answer_correct"))
    normalized = 0
    for row in answerable:
        found, _missing = facts_in(row.get("answer_text") or "", row.get("expected_facts") or [])
        if found == len(row["expected_facts"]):
            normalized += 1
    return {
        "questions": len(answerable),
        "literal_correct": wilson(literal, len(answerable)),
        "normalized_correct": wilson(normalized, len(answerable)),
    }


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(p / 100 * len(ordered)) - 1))
    return round(ordered[index], 1)


def latency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row.get("latency_ms") for row in rows if row.get("latency_ms") is not None]
    return {
        "count": len(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": round(max(values), 1) if values else None,
        "mean": round(statistics.mean(values), 1) if values else None,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "questions": len(rows),
        "retrieval": {
            "questions": sum(1 for row in rows if row.get("expected_documents")),
            "recall_at_1": recall_at(rows, 1),
            "recall_at_3": recall_at(rows, 3),
            "recall_at_5": recall_at(rows, 5),
            "recall_at_10": recall_at(rows, 10),
            "mrr": mrr(rows),
            "ndcg_at_10": ndcg_at(rows),
            "page_hit_rate": wilson(
                sum(
                    1
                    for row in rows
                    if row.get("expected_pages")
                    and any(
                        str(page) in {str(p) for p in (row.get("retrieved_pages") or [])}
                        for page in row["expected_pages"]
                    )
                ),
                sum(1 for row in rows if row.get("expected_pages")),
            ),
        },
        "answer": answer_metrics(rows),
        "refusal": refusal(rows),
        "faithfulness": {
            "questions": sum(1 for row in rows if row.get("faithfulness") is not None),
            "mean": round(
                statistics.mean(
                    [row["faithfulness"] for row in rows if row.get("faithfulness") is not None]
                ),
                4,
            )
            if any(row.get("faithfulness") is not None for row in rows)
            else None,
            "unsupported_claim_rate": round(
                statistics.mean(
                    [row["unsupported_claim_rate"] for row in rows if row.get("unsupported_claim_rate") is not None]
                ),
                4,
            )
            if any(row.get("unsupported_claim_rate") is not None for row in rows)
            else None,
        },
        "citation": {
            "questions": sum(1 for row in rows if row.get("citation_precision") is not None),
            "precision": round(
                statistics.mean([row["citation_precision"] for row in rows if row.get("citation_precision") is not None]), 4
            )
            if any(row.get("citation_precision") is not None for row in rows)
            else None,
            "recall": round(
                statistics.mean([row["citation_recall"] for row in rows if row.get("citation_recall") is not None]), 4
            )
            if any(row.get("citation_recall") is not None for row in rows)
            else None,
            "all_valid_rate": wilson(
                sum(1 for row in rows if row.get("citation_validity") == 1.0),
                sum(1 for row in rows if row.get("citation_validity") is not None),
            ),
        },
        "temporal": wilson(
            sum(1 for row in rows if row.get("temporal_correct") is True),
            sum(1 for row in rows if row.get("temporal_correct") is not None),
        ),
        "latency_ms": latency(rows),
        "tokens": {
            "prompt": sum(int(row.get("prompt_tokens") or 0) for row in rows),
            "completion": sum(int(row.get("completion_tokens") or 0) for row in rows),
        },
        "failure_taxonomy": dict(
            Counter(row.get("failure_label") or "none" for row in rows)
        ),
    }


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key))].append(row)
    return {
        name: {
            "questions": len(items),
            "answer_normalized": (answer_metrics(items)["normalized_correct"] or {}).get("rate"),
            "recall_at_10": recall_at(items, 10),
            "citation_precision": round(
                statistics.mean([r["citation_precision"] for r in items if r.get("citation_precision") is not None]), 4
            )
            if any(r.get("citation_precision") is not None for r in items)
            else None,
            "refusal_precision": refusal(items)["precision"],
            "refusal_recall": refusal(items)["recall"],
            "p50_ms": latency(items)["p50"],
        }
        for name, items in sorted(groups.items())
    }


def main() -> int:
    questions = {
        item["id"]: item for item in json.loads((V4 / "questions.json").read_text(encoding="utf-8"))["questions"]
    }
    for item in questions.values():
        item.setdefault("intent", "general")

    runs = {
        "baseline_v3": load_rows(BASE),
        "run_A": load_rows(V4 / "results" / "run_A"),
        "run_B": load_rows(V4 / "results" / "run_B"),
    }
    for name in ("run_C_1", "run_C_2"):
        rows = load_rows(V4 / "results" / name)
        if rows:
            runs[name] = rows

    out: dict[str, Any] = {"generated_from": {name: len(rows) for name, rows in runs.items()}}
    for name, rows in runs.items():
        if not rows:
            continue
        for row in rows:
            meta = questions.get(row["id"], {})
            row["intent"] = meta.get("intent", "general")
            row["origin"] = meta.get("origin", "v3")
            row["answerability"] = meta.get("answerability", row.get("answerability"))
            row.setdefault("expected_pages", meta.get("expected_pages") or [])
        out[name] = summarize(rows)
        out[name]["by_category"] = by_key(rows, "category")
        out[name]["by_intent"] = by_key(rows, "intent")
        scored = [row for row in rows if row.get("answerability") != "needs_review"]
        out[name]["scored_excluding_needs_review"] = summarize(scored)
        out[name]["by_origin"] = by_key(rows, "origin")

    # Same-question comparison: baseline and Run B on the 120 v3 ids.
    if runs["baseline_v3"] and runs["run_B"]:
        base_ids = {row["id"] for row in runs["baseline_v3"]}
        b_ids = {row["id"] for row in runs["run_B"]}
        shared = base_ids & b_ids
        base_shared = [row for row in runs["baseline_v3"] if row["id"] in shared]
        b_shared = [row for row in runs["run_B"] if row["id"] in shared]
        out["comparison_120"] = {
            "questions": len(shared),
            "baseline": summarize(base_shared),
            "run_B": summarize(b_shared),
            "delta": {
                "answer_literal": round(
                    (out["run_B"]["answer"]["literal_correct"] or {}).get("rate", 0)
                    - (summarize(base_shared)["answer"]["literal_correct"] or {}).get("rate", 0),
                    4,
                ),
                "answer_normalized": round(
                    (summarize(b_shared)["answer"]["normalized_correct"] or {}).get("rate", 0)
                    - (summarize(base_shared)["answer"]["normalized_correct"] or {}).get("rate", 0),
                    4,
                ),
                "recall_at_10": round(
                    (recall_at(b_shared, 10) or 0) - (recall_at(base_shared, 10) or 0), 4
                ),
                "mrr": round((mrr(b_shared) or 0) - (mrr(base_shared) or 0), 4),
            },
        }

    if len(runs.get("run_A", [])) and any(name.startswith("run_C") for name in runs):
        repeated = [runs[name] for name in runs if name.startswith("run_C")]
        out["variance"] = {
            "runs": len(repeated) + 1,
            "answer_normalized": [
                (summarize(rows)["answer"]["normalized_correct"] or {}).get("rate") for rows in repeated
            ],
            "note": "Run A plus the C repeats; min/max reported in REPORT.md.",
        }

    out["failures_top20"] = [
        {
            "id": row["id"],
            "category": row.get("category"),
            "question": row.get("question"),
            "expected": row.get("expected_answer"),
            "answer": (row.get("answer_text") or "")[:400],
            "retrieved": row.get("retrieved_documents"),
            "label": row.get("failure_label"),
            "facts_missing": row.get("facts_missing"),
        }
        for row in runs.get("run_A", [])
        if row.get("failure_label")
    ][:20]

    (V4 / "analysis.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    # ---------------------------------------------------------------- REPORT.md
    def pct(value: Any) -> str:
        return "—" if value is None else f"{value * 100:.1f}%"

    def line(metric: str, base: Any, new: Any, delta: Any = None) -> str:
        change = "" if delta is None else f" | {delta:+.4f}"
        return f"| {metric} | {base if base is not None else '—'} | {new if new is not None else '—'}{change} |"

    a = out.get("run_A", {})
    scored = a.get("scored_excluding_needs_review", {})
    comp = out.get("comparison_120", {})
    base_sum = comp.get("baseline", {})
    b_sum = comp.get("run_B", {})

    lines = [
        "# Benchmark v4 — rebuilt corpus and 150-question run",
        "",
        f"Generated from {len(a.get('questions', []) and runs.get('run_A', []))} Run A rows, "
        f"{len(runs.get('run_B', []))} Run B rows and {len(runs.get('baseline_v3', []))} locked baseline rows.",
        "",
        "## Headline",
        "",
        "| Metric | Old baseline (120, v3 data) | New Run B (same 120) | Δ |",
        "| --- | --- | --- | --- |",
        f"| Answer correct, literal | {pct((base_sum.get('answer', {}).get('literal_correct') or {}).get('rate'))} | "
        f"{pct((b_sum.get('answer', {}).get('literal_correct') or {}).get('rate'))} | "
        f"{comp.get('delta', {}).get('answer_literal', 0):+.4f} |",
        f"| Answer correct, normalized | {pct((base_sum.get('answer', {}).get('normalized_correct') or {}).get('rate'))} | "
        f"{pct((b_sum.get('answer', {}).get('normalized_correct') or {}).get('rate'))} | "
        f"{comp.get('delta', {}).get('answer_normalized', 0):+.4f} |",
        f"| Recall@5 | {pct(base_sum.get('retrieval', {}).get('recall_at_5'))} | {pct(b_sum.get('retrieval', {}).get('recall_at_5'))} | — |",
        f"| Recall@10 | {pct(base_sum.get('retrieval', {}).get('recall_at_10'))} | {pct(b_sum.get('retrieval', {}).get('recall_at_10'))} | "
        f"{comp.get('delta', {}).get('recall_at_10', 0):+.4f} |",
        f"| MRR | {base_sum.get('retrieval', {}).get('mrr')} | {b_sum.get('retrieval', {}).get('mrr')} | "
        f"{comp.get('delta', {}).get('mrr', 0):+.4f} |",
        f"| nDCG@10 | {base_sum.get('retrieval', {}).get('ndcg_at_10')} | {b_sum.get('retrieval', {}).get('ndcg_at_10')} | — |",
        f"| Refusal precision | {base_sum.get('refusal', {}).get('precision')} | {b_sum.get('refusal', {}).get('precision')} | — |",
        f"| Refusal recall | {base_sum.get('refusal', {}).get('recall')} | {b_sum.get('refusal', {}).get('recall')} | — |",
        "",
        "## Run A (150 questions, rebuilt corpus)",
        "",
        "| Metric | Value | n |",
        "| --- | --- | --- |",
        f"| Recall@1 / @3 / @5 / @10 | {pct(a.get('retrieval', {}).get('recall_at_1'))} / "
        f"{pct(a.get('retrieval', {}).get('recall_at_3'))} / {pct(a.get('retrieval', {}).get('recall_at_5'))} / "
        f"{pct(a.get('retrieval', {}).get('recall_at_10'))} | {a.get('retrieval', {}).get('questions')} |",
        f"| MRR | {a.get('retrieval', {}).get('mrr')} | {a.get('retrieval', {}).get('questions')} |",
        f"| nDCG@10 | {a.get('retrieval', {}).get('ndcg_at_10')} | {a.get('retrieval', {}).get('questions')} |",
        f"| Answer literal / normalized | {pct((a.get('answer', {}).get('literal_correct') or {}).get('rate'))} / "
        f"{pct((a.get('answer', {}).get('normalized_correct') or {}).get('rate'))} | {a.get('answer', {}).get('questions')} |",
        f"| Refusal precision / recall | {a.get('refusal', {}).get('precision')} / {a.get('refusal', {}).get('recall')} | {a.get('refusal', {}).get('questions')} |",
        f"| False refusals / false answers | {a.get('refusal', {}).get('fp_false_refusal')} / {a.get('refusal', {}).get('fn_false_answer')} | — |",
        f"| Citation precision / recall | {a.get('citation', {}).get('precision')} / {a.get('citation', {}).get('recall')} | {a.get('citation', {}).get('questions')} |",
        f"| Faithfulness (pipeline verdict) | {a.get('faithfulness', {}).get('mean')} | {a.get('faithfulness', {}).get('questions')} |",
        f"| Latency p50 / p95 / p99 (ms) | {a.get('latency_ms', {}).get('p50')} / "
        f"{a.get('latency_ms', {}).get('p95')} / {a.get('latency_ms', {}).get('p99')} | {a.get('latency_ms', {}).get('count')} |",
        f"| Prompt / completion tokens | {a.get('tokens', {}).get('prompt')} / {a.get('tokens', {}).get('completion')} | — |",
        "",
        "Excluding the 15 v3 items still marked `needs_review` (no adjudicated label):",
        "",
        f"- Questions: {scored.get('questions')}",
        f"- Answer literal / normalized: {pct((scored.get('answer', {}).get('literal_correct') or {}).get('rate'))} / "
        f"{pct((scored.get('answer', {}).get('normalized_correct') or {}).get('rate'))}",
        f"- Recall@5 / @10: {pct(scored.get('retrieval', {}).get('recall_at_5'))} / {pct(scored.get('retrieval', {}).get('recall_at_10'))}",
        f"- Refusal precision / recall: {scored.get('refusal', {}).get('precision')} / {scored.get('refusal', {}).get('recall')}",
        "",
        "## By category (Run A)",
        "",
        "| Category | Q | Answer (normalized) | Recall@10 | Citation P | Refusal P/R | p50 ms |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, item in a.get("by_category", {}).items():
        lines.append(
            f"| {name} | {item['questions']} | {pct(item['answer_normalized'])} | {pct(item['recall_at_10'])} | "
            f"{item['citation_precision']} | {item['refusal_precision']}/{item['refusal_recall']} | {item['p50_ms']} |"
        )

    lines += ["", "## By origin (Run A)", "", "| Origin | Q | Answer (normalized) | Recall@10 | p50 ms |", "| --- | --- | --- | --- | --- |"]
    for name, item in a.get("by_origin", {}).items():
        lines.append(
            f"| {name} | {item['questions']} | {pct(item['answer_normalized'])} | "
            f"{pct(item['recall_at_10'])} | {item['p50_ms']} |"
        )

    lines += ["", "## Failure taxonomy (Run A)", "", "| Label | Count |", "| --- | --- |"]
    for label, count in a.get("failure_taxonomy", {}).items():
        lines.append(f"| {label} | {count} |")

    (V4 / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: (out[k].get("questions") if isinstance(out.get(k), dict) else None) for k in out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
