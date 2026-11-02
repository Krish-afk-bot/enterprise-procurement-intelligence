#!/usr/bin/env python3
"""
Analyze the gap between oracle and current mode to quantify retrieval vs generation failures.

Usage:
    python scripts_phase3/analyze_oracle_gap.py --dev
    python scripts_phase3/analyze_oracle_gap.py --held-out
"""
import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"


def load_report(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def analyze_gap(current: dict, oracle: dict) -> str:
    """Generate one-paragraph analysis of the oracle vs current gap."""
    lines = []
    lines.append("## Oracle vs Current Mode Analysis\n")
    
    # Answer correctness
    cur_correct = current["answer"]["correct"]
    ora_correct = oracle["answer"]["correct"]
    correctness_gap = ora_correct["rate"] - cur_correct["rate"]
    
    lines.append(f"**Answer Correctness**: current {cur_correct['rate']:.1%} → oracle {ora_correct['rate']:.1%}")
    lines.append(f"(+{correctness_gap:.1%}, {int(correctness_gap * cur_correct['total'])} questions)\n")
    
    # Refusal precision/recall
    cur_prec = float(current["refusal"]["precision"])
    ora_prec = float(oracle["refusal"]["precision"])
    cur_rec = float(current["refusal"]["recall"])
    ora_rec = float(oracle["refusal"]["recall"])
    
    lines.append(f"**Refusal Precision**: current {cur_prec:.3f} → oracle {ora_prec:.3f} ({ora_prec - cur_prec:+.3f})\n")
    lines.append(f"**Refusal Recall**: current {cur_rec:.3f} → oracle {ora_rec:.3f} ({ora_rec - cur_rec:+.3f})\n")
    
    # Failure taxonomy comparison
    lines.append("**Failure Taxonomy**:\n")
    lines.append("| Label | Current | Oracle | Interpretation |")
    lines.append("|-------|---------|--------|----------------|")
    
    cur_tax = current["failure_taxonomy"]
    ora_tax = oracle["failure_taxonomy"]
    
    for label in sorted(set(cur_tax.keys()) | set(ora_tax.keys())):
        cur_count = cur_tax.get(label, 0)
        ora_count = ora_tax.get(label, 0)
        delta = ora_count - cur_count
        
        if label == "retrieval_miss":
            interp = f"{-delta} fixed by gold chunks (retrieval gap)"
        elif label == "wrong_context_selected":
            interp = f"{-delta} passages retrieved but dropped"
        elif label == "generation_error":
            interp = "generation/LLM limitation (persists in oracle)"
        elif label == "refusal_failure":
            interp = "over/under-refusal (verification issue)"
        else:
            interp = ""
        
        lines.append(f"| {label} | {cur_count} | {ora_count} | {interp} |")
    
    lines.append("")
    
    # Interpretation paragraph
    retrieval_gap = cur_tax.get("retrieval_miss", 0) + cur_tax.get("wrong_context_selected", 0)
    retrieval_gap -= ora_tax.get("retrieval_miss", 0) + ora_tax.get("wrong_context_selected", 0)
    
    generation_gap = ora_tax.get("generation_error", 0) + ora_tax.get("refusal_failure", 0)
    
    total_failures = current["failures_total"]
    
    if retrieval_gap > 0:
        retrieval_pct = (retrieval_gap / total_failures) * 100
    else:
        retrieval_pct = 0
    
    if generation_gap > 0:
        generation_pct = (generation_gap / total_failures) * 100
    else:
        generation_pct = 0
    
    lines.append("### Interpretation\n")
    lines.append(
        f"The {correctness_gap:.1%} correctness gap between current and oracle mode "
        f"indicates that **{retrieval_gap} failures ({retrieval_pct:.0f}% of {total_failures} total) "
        f"are due to retrieval** (missing or dropped evidence). "
    )
    lines.append(
        f"**{generation_gap} failures ({generation_pct:.0f}%) persist in oracle mode**, "
        f"indicating generation or verification issues that cannot be fixed by better retrieval alone. "
    )
    
    if cur_prec < ora_prec:
        lines.append(
            f"Refusal precision improved from {cur_prec:.3f} to {ora_prec:.3f} in oracle mode, "
            f"suggesting some false refusals are caused by insufficient retrieved evidence."
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze oracle vs current gap")
    parser.add_argument("--dev", action="store_true", help="analyze dev set")
    parser.add_argument("--held-out", action="store_true", help="analyze held-out set")
    parser.add_argument("--label", default="dev-baseline", help="label prefix for files")
    parser.add_argument("--model", default="qwen2.5-coder-7b", help="model slug")
    args = parser.parse_args()
    
    if not args.dev and not args.held_out:
        print("Error: specify --dev or --held-out")
        return 1
    
    dataset = "dev" if args.dev else "held-out"
    
    current_file = EVAL_DIR / f"{args.label}_{dataset}_current_{args.model}.json"
    oracle_file = EVAL_DIR / f"{args.label}_{dataset}_oracle_{args.model}.json"
    
    if not current_file.exists():
        print(f"Error: {current_file} not found. Run evaluation first:")
        print(f"  python scripts_phase3/eval_v2.py --mode both --dataset {dataset} --label {args.label}")
        return 1
    
    if not oracle_file.exists():
        print(f"Error: {oracle_file} not found. Run oracle mode:")
        print(f"  python scripts_phase3/eval_v2.py --mode oracle --dataset {dataset} --label {args.label}")
        return 1
    
    current = load_report(current_file)
    oracle = load_report(oracle_file)
    
    analysis = analyze_gap(current, oracle)
    print(analysis)
    
    # Write to file
    output_file = PROJECT_ROOT / "docs" / "results" / f"oracle-gap-{dataset}.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(analysis, encoding="utf-8")
    print(f"\nAnalysis written to {output_file.relative_to(PROJECT_ROOT)}")
    
    return 0


if __name__ == "__main__":
    exit(main())
