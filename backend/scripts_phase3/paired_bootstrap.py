#!/usr/bin/env python3
"""
Paired bootstrap comparison for evaluation metrics.

Computes 95% confidence interval for the difference between two evaluation runs
using paired bootstrap resampling (1000 resamples by default).

Usage:
    python scripts_phase3/paired_bootstrap.py \\
        --before data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json \\
        --after data/evaluation/v2/dev-after-fix-1_dev_current_qwen2.5-coder-7b.json \\
        --metric answer.correct
"""
import argparse
import json
import numpy as np
from pathlib import Path
from typing import Any

def load_report(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_metric_values(report: dict, metric_path: str) -> list[float | bool]:
    """Extract per-question values for a metric.
    
    Args:
        report: evaluation report dict
        metric_path: dot-separated path like "answer.correct" or "refusal.precision"
    
    Returns:
        list of per-question values (0/1 for binary metrics, float for continuous)
    """
    rows = report.get("rows", [])
    
    if metric_path == "answer.correct":
        return [1.0 if row.get("answer_correct") else 0.0 for row in rows]
    
    elif metric_path == "refusal.false_refusal":
        # false refusal: expected_refusal=false but status=insufficient_evidence or refused
        values = []
        for row in rows:
            expected_refusal = row.get("expected_refusal", False)
            status = row.get("status", "")
            if not expected_refusal and status in ("insufficient_evidence", "refused"):
                values.append(1.0)
            else:
                values.append(0.0)
        return values
    
    elif metric_path == "refusal.precision":
        # This is aggregate-level, need to compute from per-question TP/FP
        # For paired comparison, we need per-question contribution
        # Precision = TP / (TP + FP), so each question contributes to TP or FP
        values = []
        for row in rows:
            expected_refusal = row.get("expected_refusal", False)
            status = row.get("status", "")
            actually_refused = status in ("insufficient_evidence", "refused")
            
            if actually_refused:
                # This is a refusal - it's either TP or FP
                if expected_refusal:
                    values.append(1.0)  # TP
                else:
                    values.append(0.0)  # FP
            else:
                values.append(None)  # Did not refuse, not counted in precision
        return [v for v in values if v is not None]
    
    elif metric_path == "citation.precision":
        return [row.get("citation_precision", 0.0) for row in rows]
    
    elif metric_path == "latency_ms":
        return [row.get("latency_ms", 0.0) for row in rows]
    
    else:
        raise ValueError(f"Unknown metric path: {metric_path}")


def paired_bootstrap_test(
    before_values: list[float],
    after_values: list[float],
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Perform paired bootstrap test.
    
    Args:
        before_values: per-question values from before run
        after_values: per-question values from after run (same order)
        n_resamples: number of bootstrap resamples
        confidence_level: confidence level (0.95 for 95% CI)
    
    Returns:
        dict with mean_diff, ci_low, ci_high, significant
    """
    if len(before_values) != len(after_values):
        raise ValueError(f"Length mismatch: {len(before_values)} vs {len(after_values)}")
    
    n = len(before_values)
    if n == 0:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "significant": False, "n": 0}
    
    before = np.array(before_values)
    after = np.array(after_values)
    
    # Observed difference
    observed_diff = np.mean(after) - np.mean(before)
    
    # Bootstrap resampling
    rng = np.random.default_rng(seed=42)
    bootstrap_diffs = []
    
    for _ in range(n_resamples):
        # Resample indices (with replacement)
        indices = rng.choice(n, size=n, replace=True)
        before_resample = before[indices]
        after_resample = after[indices]
        diff = np.mean(after_resample) - np.mean(before_resample)
        bootstrap_diffs.append(diff)
    
    # Confidence interval
    alpha = 1 - confidence_level
    ci_low = np.percentile(bootstrap_diffs, 100 * alpha / 2)
    ci_high = np.percentile(bootstrap_diffs, 100 * (1 - alpha / 2))
    
    # Significant if CI excludes 0
    significant = not (ci_low <= 0 <= ci_high)
    
    return {
        "mean_diff": observed_diff,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "significant": significant,
        "n": n,
        "n_resamples": n_resamples,
        "confidence_level": confidence_level,
    }


def main():
    parser = argparse.ArgumentParser(description="Paired bootstrap comparison")
    parser.add_argument("--before", required=True, help="path to before results JSON")
    parser.add_argument("--after", required=True, help="path to after results JSON")
    parser.add_argument("--metric", required=True, help="metric to compare (e.g., answer.correct)")
    parser.add_argument("--n-resamples", type=int, default=1000, help="number of bootstrap resamples")
    args = parser.parse_args()
    
    before_report = load_report(Path(args.before))
    after_report = load_report(Path(args.after))
    
    before_values = get_metric_values(before_report, args.metric)
    after_values = get_metric_values(after_report, args.metric)
    
    result = paired_bootstrap_test(before_values, after_values, n_resamples=args.n_resamples)
    
    print(f"\nMetric: {args.metric}")
    print(f"N: {result['n']}")
    print(f"Mean difference: {result['mean_diff']:.4f}")
    print(f"95% CI: [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
    print(f"Significant: {result['significant']}")
    
    if result['significant']:
        direction = "improved" if result['mean_diff'] > 0 else "degraded"
        print(f"\nConclusion: The metric {direction} with 95% confidence.")
    else:
        print(f"\nConclusion: No significant difference detected (CI includes 0).")
    
    return 0


if __name__ == "__main__":
    exit(main())
