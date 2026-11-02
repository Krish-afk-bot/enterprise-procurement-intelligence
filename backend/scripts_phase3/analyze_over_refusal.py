#!/usr/bin/env python3
"""
Analyze false refusals on dev set to understand why the system over-refuses.

For each false refusal:
- Record category
- Record which check refused (coverage, claim binding, grounding, answerability)
- Record evidence status: in retrieved hits, in final context, or missing

Output: markdown table in docs/results/over-refusal.md

Usage:
    python scripts_phase3/analyze_over_refusal.py --dev --output ../docs/results/over-refusal.md
"""
import argparse
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"


def analyze_refusal_reason(row: dict) -> str:
    """Determine which check caused the refusal."""
    state = row.get("state", {})
    status = row.get("status", "unknown")
    
    # Check verification output
    verification = state.get("verification", {})
    grounding_score = verification.get("grounding_score", 1.0)
    supported_claims = verification.get("supported_claims", 0)
    total_claims = verification.get("total_claims", 0)
    
    # Check evidence evaluation
    evidence_eval = state.get("evidence_evaluation", {})
    coverage = evidence_eval.get("coverage", True)
    claim_binding = evidence_eval.get("claim_binding", {}).get("satisfied", True)
    
    # Determine reason
    if status == "insufficient_evidence":
        if not coverage:
            return "coverage_check"
        elif not claim_binding:
            return "claim_binding"
        elif grounding_score < 0.5:
            return "grounding_score_low"
        elif total_claims > 0 and supported_claims == 0:
            return "no_supported_claims"
        else:
            return "answerability_other"
    elif status == "refused":
        return "explicit_refusal"
    else:
        return "unknown"


def check_evidence_location(row: dict, question: dict) -> str:
    """Determine if needed evidence was retrieved, in context, or missing."""
    expected_docs = set(question.get("expected_documents", []))
    if not expected_docs:
        return "n/a"
    
    state = row.get("state", {})
    retrieval = state.get("retrieval", {})
    hits = retrieval.get("hits", [])
    
    # Check if any expected doc is in retrieved hits
    retrieved_docs = set()
    for hit in hits:
        doc_name = hit.get("document_name", "")
        retrieved_docs.add(doc_name)
    
    if expected_docs & retrieved_docs:
        # At least one expected doc was retrieved
        # Check if it made it to the final context
        context_used = state.get("context", {}).get("chunks_used", [])
        if not context_used:
            # Try to infer from hits that were used
            context_used = [h for h in hits if h.get("used", True)]
        
        context_docs = set()
        for chunk in context_used:
            doc_name = chunk.get("document_name", "")
            context_docs.add(doc_name)
        
        if expected_docs & context_docs:
            return "in_context"
        else:
            return "retrieved_not_in_context"
    else:
        return "not_retrieved"


def analyze_over_refusal(results_file: Path, questions_file: Path) -> str:
    """Generate over-refusal analysis table."""
    with open(results_file) as f:
        results = json.load(f)
    
    with open(questions_file) as f:
        questions_data = json.load(f)
    
    questions_by_id = {q["id"]: q for q in questions_data["questions"]}
    
    # Find false refusals (expected_refusal=false but status=insufficient_evidence or refused)
    false_refusals = []
    
    for row in results.get("rows", []):
        question = questions_by_id.get(row["id"])
        if not question:
            continue
        
        if question.get("expected_refusal", False):
            continue  # Not a false refusal
        
        status = row.get("status", "")
        if status in ("insufficient_evidence", "refused"):
            reason = analyze_refusal_reason(row)
            evidence = check_evidence_location(row, question)
            
            false_refusals.append({
                "id": row["id"],
                "question": row.get("question", ""),
                "category": question.get("category", "unknown"),
                "refusal_reason": reason,
                "evidence_location": evidence,
                "expected_docs": ", ".join(question.get("expected_documents", [])),
            })
    
    # Generate markdown
    lines = []
    lines.append("# Over-Refusal Analysis (Dev Set)\n")
    lines.append(f"**Total false refusals**: {len(false_refusals)}\n")
    
    # Summary counts
    lines.append("## Summary\n")
    
    reason_counts = Counter(fr["refusal_reason"] for fr in false_refusals)
    lines.append("### By Refusal Reason:\n")
    for reason, count in reason_counts.most_common():
        lines.append(f"- {reason}: {count}")
    
    lines.append("")
    
    evidence_counts = Counter(fr["evidence_location"] for fr in false_refusals)
    lines.append("### By Evidence Location:\n")
    for location, count in evidence_counts.most_common():
        lines.append(f"- {location}: {count}")
    
    lines.append("")
    
    category_counts = Counter(fr["category"] for fr in false_refusals)
    lines.append("### By Category:\n")
    for category, count in category_counts.most_common():
        lines.append(f"- {category}: {count}")
    
    lines.append("\n## Detailed Table\n")
    lines.append("| ID | Category | Refusal Reason | Evidence Location | Expected Docs |")
    lines.append("|----|----------|----------------|-------------------|---------------|")
    
    for fr in sorted(false_refusals, key=lambda x: x["category"]):
        lines.append(
            f"| {fr['id']} | {fr['category']} | {fr['refusal_reason']} | "
            f"{fr['evidence_location']} | {fr['expected_docs'][:50]} |"
        )
    
    lines.append("\n## Interpretation\n")
    
    if reason_counts:
        top_reason = reason_counts.most_common(1)[0]
        lines.append(
            f"The most common refusal reason is **{top_reason[0]}** ({top_reason[1]} cases). "
            f"This should be addressed first."
        )
    
    if evidence_counts:
        retrieved_but_dropped = evidence_counts.get("retrieved_not_in_context", 0)
        if retrieved_but_dropped > 0:
            lines.append(
                f"\n**{retrieved_but_dropped} questions** had the needed evidence retrieved "
                f"but it was dropped before reaching the final context. This suggests the context "
                f"builder is cutting relevant passages."
            )
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze over-refusal on dev set")
    parser.add_argument("--dev", action="store_true", required=True, help="analyze dev set only")
    parser.add_argument("--output", required=True, help="output markdown file")
    parser.add_argument("--label", default="dev-baseline", help="label prefix for results file")
    parser.add_argument("--model", default="qwen2.5-coder-7b", help="model slug")
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
    
    analysis = analyze_over_refusal(results_file, questions_file)
    print(analysis)
    
    # Write to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(analysis, encoding="utf-8")
    print(f"\nAnalysis written to {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
