#!/usr/bin/env python3
"""
Analyze ALL failures on dev set to understand improvement opportunities.

Categorizes failures into:
1. False refusals (should answer but didn't) - 17 cases
2. Under-refusals (should refuse but didn't) - 3 cases
3. Wrong answers (answered but incorrectly) - 6 cases

For each failure, determine:
- Root cause category
- Whether retrieval was the issue
- Specific failure mode

Output: markdown table in docs/results/all-failures.md

Usage:
    python scripts_phase3/analyze_all_failures.py --label dev-baseline --output docs/results/all-failures.md
"""
import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"

# Handle both backend/scripts_phase3 and scripts_phase3 paths
if not EVAL_DIR.exists():
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"


def check_retrieval_quality(row: dict, question: dict) -> dict:
    """Check if retrieval succeeded."""
    expected_docs = set(question.get("expected_documents", []))
    if not expected_docs:
        return {"has_expected_docs": False, "status": "n/a"}
    
    state = row.get("state", {})
    retrieval = state.get("retrieval", {})
    hits = retrieval.get("hits", [])
    
    # Check if any expected doc is in top-10 hits
    retrieved_docs = set()
    context_docs = set()
    
    for hit in hits[:10]:  # Top-10 for recall@10
        doc_name = hit.get("document_name", "")
        retrieved_docs.add(doc_name)
    
    # Check what made it to context
    context_used = state.get("context", {}).get("chunks_used", [])
    if not context_used:
        context_used = [h for h in hits if h.get("used", True)]
    
    for chunk in context_used:
        doc_name = chunk.get("document_name", "")
        context_docs.add(doc_name)
    
    if expected_docs & retrieved_docs:
        if expected_docs & context_docs:
            return {"has_expected_docs": True, "status": "in_context", "is_retrieval_issue": False}
        else:
            return {"has_expected_docs": True, "status": "retrieved_not_in_context", "is_retrieval_issue": True}
    else:
        return {"has_expected_docs": True, "status": "not_retrieved", "is_retrieval_issue": True}


def categorize_false_refusal(row: dict, question: dict, retrieval_info: dict) -> dict:
    """Categorize why a false refusal occurred."""
    state = row.get("state", {})
    
    # If retrieval failed, that's the root cause
    if retrieval_info.get("is_retrieval_issue"):
        return {
            "failure_type": "false_refusal",
            "root_cause": "retrieval_failure",
            "subcause": retrieval_info["status"],
            "is_retrieval_issue": True,
        }
    
    # Evidence was in context but system still refused
    # Check what component triggered refusal
    status = row.get("status", "unknown")
    evidence_eval = state.get("evidence_evaluation", {})
    verification = state.get("verification", {})
    
    coverage = evidence_eval.get("coverage", True)
    claim_binding = evidence_eval.get("claim_binding", {}).get("satisfied", True)
    grounding_score = verification.get("grounding_score", 1.0)
    
    if not coverage:
        subcause = "coverage_check_failed"
    elif not claim_binding:
        subcause = "claim_binding_failed"
    elif grounding_score < 0.5:
        subcause = "grounding_score_too_low"
    else:
        subcause = "answerability_other"
    
    return {
        "failure_type": "false_refusal",
        "root_cause": "reasoning_failure",
        "subcause": subcause,
        "is_retrieval_issue": False,
    }


def categorize_under_refusal(row: dict, question: dict) -> dict:
    """Categorize why an under-refusal occurred (answered when should refuse)."""
    # These are questions where expected_refusal=true but system answered anyway
    return {
        "failure_type": "under_refusal",
        "root_cause": "refusal_gate_missed",
        "subcause": "should_have_refused",
        "is_retrieval_issue": False,
    }


def categorize_wrong_answer(row: dict, question: dict, retrieval_info: dict) -> dict:
    """Categorize why answer was wrong."""
    state = row.get("state", {})
    
    # If retrieval failed, that's likely the root cause
    if retrieval_info.get("is_retrieval_issue"):
        return {
            "failure_type": "wrong_answer",
            "root_cause": "retrieval_failure",
            "subcause": retrieval_info["status"],
            "is_retrieval_issue": True,
        }
    
    # Evidence was in context but answer is wrong
    # This is a reasoning/extraction failure
    verification = state.get("verification", {})
    grounding_score = verification.get("grounding_score", 1.0)
    
    if grounding_score < 0.7:
        subcause = "poor_grounding"
    else:
        subcause = "reasoning_error"
    
    return {
        "failure_type": "wrong_answer",
        "root_cause": "reasoning_failure",
        "subcause": subcause,
        "is_retrieval_issue": False,
    }


def analyze_all_failures(results_file: Path, questions_file: Path) -> dict:
    """Analyze all failures and return structured data."""
    with open(results_file) as f:
        results = json.load(f)
    
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    questions_by_id = {q["id"]: q for q in questions_data["questions"]}
    
    failures = []
    
    for row in results.get("rows", []):
        question = questions_by_id.get(row["id"])
        if not question:
            continue
        
        # Determine failure type
        expected_refusal = question.get("expected_refusal", False)
        refused = row.get("refused", False)
        answer_correct = row.get("answer_correct", False)
        
        # Check if this is a failure
        if expected_refusal:
            # For unanswerable: correct = refused
            if refused:
                continue  # Correctly refused
            else:
                # Under-refusal (answered when should refuse)
                category = categorize_under_refusal(row, question)
        else:
            # For answerable: correct = answer_correct AND not refused
            if answer_correct and not refused:
                continue  # Correctly answered
            
            retrieval_info = check_retrieval_quality(row, question)
            
            if refused:
                # False refusal
                category = categorize_false_refusal(row, question, retrieval_info)
            else:
                # Wrong answer
                category = categorize_wrong_answer(row, question, retrieval_info)
        
        failures.append({
            "id": row["id"],
            "question": row.get("question", "")[:80],
            "category": question.get("category", "unknown"),
            "expected_docs": ", ".join(question.get("expected_documents", []))[:50],
            **category,
        })
    
    return failures


def generate_markdown_report(failures: list) -> str:
    """Generate markdown report from failures."""
    lines = []
    lines.append("# All Failures Analysis (Dev Set)\n")
    lines.append(f"**Total failures**: {len(failures)}\n")
    
    # Count by failure type
    type_counts = Counter(f["failure_type"] for f in failures)
    lines.append("## By Failure Type\n")
    for ftype, count in type_counts.most_common():
        pct = 100 * count / len(failures)
        lines.append(f"- **{ftype}**: {count} ({pct:.1f}%)")
    lines.append("")
    
    # Count by root cause
    cause_counts = Counter(f["root_cause"] for f in failures)
    lines.append("## By Root Cause\n")
    for cause, count in cause_counts.most_common():
        pct = 100 * count / len(failures)
        lines.append(f"- **{cause}**: {count} ({pct:.1f}%)")
    lines.append("")
    
    # Retrieval vs non-retrieval
    retrieval_issues = sum(1 for f in failures if f["is_retrieval_issue"])
    non_retrieval = len(failures) - retrieval_issues
    lines.append("## Retrieval vs Non-Retrieval Issues\n")
    lines.append(f"- **Retrieval issues**: {retrieval_issues} ({100*retrieval_issues/len(failures):.1f}%)")
    lines.append(f"- **Non-retrieval issues**: {non_retrieval} ({100*non_retrieval/len(failures):.1f}%)")
    lines.append("")
    
    # Breakdown by subcause
    subcause_counts = Counter(f["subcause"] for f in failures)
    lines.append("## By Subcause\n")
    for subcause, count in subcause_counts.most_common():
        pct = 100 * count / len(failures)
        lines.append(f"- **{subcause}**: {count} ({pct:.1f}%)")
    lines.append("")
    
    # Cross-tab: failure type × root cause
    lines.append("## Cross-Tabulation: Failure Type × Root Cause\n")
    lines.append("| Failure Type | Retrieval | Reasoning | Refusal Gate | Total |")
    lines.append("|--------------|-----------|-----------|--------------|-------|")
    
    for ftype in ["false_refusal", "under_refusal", "wrong_answer"]:
        ftype_failures = [f for f in failures if f["failure_type"] == ftype]
        retrieval_count = sum(1 for f in ftype_failures if f["root_cause"] == "retrieval_failure")
        reasoning_count = sum(1 for f in ftype_failures if f["root_cause"] == "reasoning_failure")
        refusal_count = sum(1 for f in ftype_failures if f["root_cause"] == "refusal_gate_missed")
        total = len(ftype_failures)
        lines.append(f"| {ftype} | {retrieval_count} | {reasoning_count} | {refusal_count} | {total} |")
    
    lines.append("")
    
    # Detailed table
    lines.append("## Detailed Failure Table\n")
    lines.append("| ID | Type | Root Cause | Subcause | Category |")
    lines.append("|----|------|------------|----------|----------|")
    
    for f in sorted(failures, key=lambda x: (x["failure_type"], x["root_cause"])):
        lines.append(
            f"| {f['id']} | {f['failure_type']} | {f['root_cause']} | "
            f"{f['subcause']} | {f['category']} |"
        )
    
    lines.append("")
    
    # Key insights
    lines.append("## Key Insights\n")
    
    if retrieval_issues > 0:
        lines.append(
            f"1. **Retrieval issues**: {retrieval_issues}/{len(failures)} failures "
            f"({100*retrieval_issues/len(failures):.1f}%) are due to retrieval problems. "
            f"Improving retrieval could fix these.\n"
        )
    
    if non_retrieval > 0:
        lines.append(
            f"2. **Non-retrieval issues**: {non_retrieval}/{len(failures)} failures "
            f"({100*non_retrieval/len(failures):.1f}%) occur even when correct evidence is in context. "
            f"These require prompt/reasoning improvements, not retrieval changes.\n"
        )
    
    # Find most common non-retrieval subcause
    non_retrieval_failures = [f for f in failures if not f["is_retrieval_issue"]]
    if non_retrieval_failures:
        nr_subcause_counts = Counter(f["subcause"] for f in non_retrieval_failures)
        top_nr_subcause = nr_subcause_counts.most_common(1)[0]
        lines.append(
            f"3. **Top non-retrieval issue**: {top_nr_subcause[0]} "
            f"({top_nr_subcause[1]} cases). Focus here for reasoning improvements.\n"
        )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze all failures on dev set")
    parser.add_argument("--label", default="dev-baseline", help="label prefix for results file")
    parser.add_argument("--model", default="qwen2.5-coder-7b", help="model slug")
    parser.add_argument("--output", default="docs/results/all-failures.md", help="output markdown file")
    args = parser.parse_args()
    
    results_file = EVAL_DIR / f"{args.label}_dev_current_{args.model}.json"
    questions_file = EVAL_DIR / "questions_dev.json"
    
    if not results_file.exists():
        print(f"Error: {results_file} not found. Run evaluation first:")
        print(f"  python scripts_phase3/eval_v2.py --mode current --dataset dev --label {args.label}")
        return 1
    
    if not questions_file.exists():
        print(f"Error: {questions_file} not found. Run create_holdout_split.py first.")
        return 1
    
    print("Analyzing all failures...")
    failures = analyze_all_failures(results_file, questions_file)
    
    print(f"Found {len(failures)} total failures\n")
    
    # Generate report
    report = generate_markdown_report(failures)
    print(report)
    
    # Write to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n✓ Analysis written to {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
