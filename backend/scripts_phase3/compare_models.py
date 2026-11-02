#!/usr/bin/env python3
"""
Compare multiple model runs side-by-side.

Usage:
    python scripts_phase3/compare_models.py dev-coder dev-instruct dev-14b
"""
import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"


def load_report(label: str, dataset: str = "dev") -> dict | None:
    """Find and load a report by label."""
    pattern = f"{label}_{dataset}_current_*.json"
    matches = list(EVAL_DIR.glob(pattern))
    if not matches:
        return None
    return json.loads(matches[0].read_text())


def format_rate(block: dict | None) -> str:
    if not block:
        return "n/a"
    return f"{block['rate']:.1%}"


def compare_models(*labels: str, dataset: str = "dev") -> str:
    """Generate comparison table for multiple model runs."""
    reports = {}
    for label in labels:
        report = load_report(label, dataset)
        if report:
            reports[label] = report
        else:
            print(f"Warning: No report found for label '{label}'")
    
    if not reports:
        return "Error: No valid reports found"
    
    lines = [f"# Model Comparison ({dataset} set)", ""]
    
    # Basic info
    lines.append("## Run Information\n")
    lines.append("| Label | Model | Questions | Duration (s) |")
    lines.append("|-------|-------|-----------|--------------|")
    for label, report in reports.items():
        run = report["run"]
        lines.append(
            f"| {label} | {run['llm_model']} | {report['dataset']['question_count']} | {run['duration_seconds']} |"
        )
    lines.append("")
    
    # Answer correctness
    lines.append("## Answer Correctness\n")
    lines.append("| Label | Correctness | Mean Fact Coverage |")
    lines.append("|-------|-------------|-------------------|")
    for label, report in reports.items():
        a = report["answer"]
        lines.append(f"| {label} | {format_rate(a['correct'])} | {a['mean_fact_coverage']:.3f} |")
    lines.append("")
    
    # Refusal
    lines.append("## Refusal Behavior\n")
    lines.append("| Label | Precision | Recall | TP | FP | FN | TN |")
    lines.append("|-------|-----------|--------|----|----|----|----|")
    for label, report in reports.items():
        f = report["refusal"]
        lines.append(
            f"| {label} | {f['precision']} | {f['recall']} | "
            f"{f['tp']} | {f['fp']} | {f['fn']} | {f['tn']} |"
        )
    lines.append("")
    
    # Citation
    lines.append("## Citation Quality\n")
    lines.append("| Label | Mean Precision | No Unsupported |")
    lines.append("|-------|---------------|----------------|")
    for label, report in reports.items():
        c = report["citation"]
        lines.append(
            f"| {label} | {c['mean_precision']:.3f} | {format_rate(c['no_unsupported_citations'])} |"
        )
    lines.append("")
    
    # Latency
    lines.append("## Latency (ms)\n")
    lines.append("| Label | p50 | p95 | max | mean |")
    lines.append("|-------|-----|-----|-----|------|")
    for label, report in reports.items():
        lat = report["latency_ms"]
        lines.append(f"| {label} | {lat['p50']} | {lat['p95']} | {lat['max']} | {lat['mean']:.0f} |")
    lines.append("")
    
    # Failure taxonomy
    lines.append("## Failure Taxonomy\n")
    all_labels_set = set()
    for report in reports.values():
        all_labels_set.update(report["failure_taxonomy"].keys())
    
    lines.append("| Failure Label | " + " | ".join(reports.keys()) + " |")
    lines.append("|" + "---|" * (len(reports) + 1))
    
    for fail_label in sorted(all_labels_set):
        counts = [str(report["failure_taxonomy"].get(fail_label, 0)) for report in reports.values()]
        lines.append(f"| {fail_label} | " + " | ".join(counts) + " |")
    
    lines.append(f"| **TOTAL** | " + " | ".join(str(r["failures_total"]) for r in reports.values()) + " |")
    lines.append("")
    
    # Interpretation
    lines.append("## Interpretation\n")
    
    # Find best and worst for key metrics
    correctness_scores = {label: report["answer"]["correct"]["rate"] for label, report in reports.items()}
    best_correct = max(correctness_scores.items(), key=lambda x: x[1])
    
    fp_counts = {label: report["refusal"]["fp"] for label, report in reports.items()}
    fewest_fp = min(fp_counts.items(), key=lambda x: x[1])
    
    lines.append(f"**Best answer correctness**: {best_correct[0]} ({best_correct[1]:.1%})")
    lines.append(f"**Fewest false refusals (FP)**: {fewest_fp[0]} ({fewest_fp[1]} false positives)")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare multiple model runs")
    parser.add_argument("labels", nargs="+", help="labels to compare (e.g., dev-coder dev-instruct)")
    parser.add_argument("--dataset", default="dev", choices=["dev", "held-out"], help="dataset to compare")
    parser.add_argument("--output", help="output markdown file (optional)")
    args = parser.parse_args()
    
    comparison = compare_models(*args.labels, dataset=args.dataset)
    print(comparison)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(comparison, encoding="utf-8")
        print(f"\nComparison written to {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
