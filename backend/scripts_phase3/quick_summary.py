#!/usr/bin/env python3
"""
Quick summary of evaluation results - useful while waiting for oracle to complete.

Usage:
    python scripts_phase3/quick_summary.py data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json
"""
import argparse
import json
from pathlib import Path


def summarize(report_path: Path) -> str:
    with open(report_path) as f:
        report = json.load(f)
    
    run = report["run"]
    answer = report["answer"]
    refusal = report["refusal"]
    taxonomy = report["failure_taxonomy"]
    
    lines = []
    lines.append(f"# Quick Summary: {run['mode']} mode\n")
    lines.append(f"**Model**: {run['llm_model']}")
    lines.append(f"**Questions**: {report['dataset']['question_count']}")
    lines.append(f"**Duration**: {run['duration_seconds']:.0f}s\n")
    
    lines.append("## Key Metrics\n")
    lines.append(f"- Answer correctness: **{answer['correct']['rate']:.1%}** ({answer['correct']['tp']}/{answer['questions']})")
    lines.append(f"- Refusal precision: **{refusal['precision']}** (TP={refusal['tp']}, FP={refusal['fp']})")
    lines.append(f"- Refusal recall: **{refusal['recall']}** (TP={refusal['tp']}, FN={refusal['fn']})")
    lines.append(f"- Total failures: **{report['failures_total']}**\n")
    
    lines.append("## Failure Breakdown\n")
    for label, count in sorted(taxonomy.items(), key=lambda x: -x[1]):
        if count > 0:
            pct = (count / report['failures_total']) * 100 if report['failures_total'] > 0 else 0
            lines.append(f"- **{label}**: {count} ({pct:.0f}%)")
    
    lines.append("\n## Interpretation\n")
    
    if taxonomy.get("refusal_failure", 0) > taxonomy.get("retrieval_miss", 0):
        lines.append(
            f"**Over-refusal is the primary issue** ({taxonomy.get('refusal_failure', 0)} failures). "
            f"The system refuses answerable questions, likely due to coverage/binding/grounding checks."
        )
    
    if taxonomy.get("retrieval_miss", 0) > 0:
        lines.append(
            f"\n**Retrieval misses** ({taxonomy.get('retrieval_miss', 0)} failures) indicate "
            f"that some expected documents didn't reach the top-k."
        )
    
    if taxonomy.get("wrong_context_selected", 0) > 0:
        lines.append(
            f"\n**Context selection issues** ({taxonomy.get('wrong_context_selected', 0)} failures) "
            f"suggest retrieved documents were dropped before generation."
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Quick evaluation summary")
    parser.add_argument("report", help="path to evaluation JSON file")
    args = parser.parse_args()
    
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Error: {report_path} not found")
        return 1
    
    summary = summarize(report_path)
    print(summary)
    
    # Write to markdown
    output_path = report_path.parent / f"{report_path.stem}_summary.md"
    output_path.write_text(summary, encoding="utf-8")
    print(f"\nSummary written to {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
