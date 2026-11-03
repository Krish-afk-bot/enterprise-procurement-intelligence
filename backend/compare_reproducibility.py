#!/usr/bin/env python3
"""Compare two baseline runs for reproducibility."""
import json
from pathlib import Path

run1 = json.load(open('../data/evaluation/v2/reproducibility-run1_dev_current_qwen2.5-coder-7b.json'))
run2 = json.load(open('../data/evaluation/v2/reproducibility-run2_dev_current_qwen2.5-coder-7b.json'))

print("=" * 80)
print("REPRODUCIBILITY COMPARISON: Run1 vs Run2")
print("=" * 80)
print()

print("Answer Correctness:")
print(f"  Run1: {run1['answer']['correct']['rate']:.4f} ({run1['answer']['correct']['successes']}/{run1['answer']['correct']['total']})")
print(f"  Run2: {run2['answer']['correct']['rate']:.4f} ({run2['answer']['correct']['successes']}/{run2['answer']['correct']['total']})")
print(f"  Difference: {abs(run1['answer']['correct']['rate'] - run2['answer']['correct']['rate']):.4f} ({abs(run1['answer']['correct']['successes'] - run2['answer']['correct']['successes'])} questions)")
print()

print("Refusal Metrics:")
print(f"  Precision:")
print(f"    Run1: {run1['refusal']['precision']:.4f}")
print(f"    Run2: {run2['refusal']['precision']:.4f}")
print(f"    Difference: {abs(run1['refusal']['precision'] - run2['refusal']['precision']):.4f}")
print(f"  Recall:")
print(f"    Run1: {run1['refusal']['recall']:.4f}")
print(f"    Run2: {run2['refusal']['recall']:.4f}")
print(f"    Difference: {abs(run1['refusal']['recall'] - run2['refusal']['recall']):.4f}")
print()

print("Refusal Confusion Matrix:")
print(f"  Run1: TP={run1['refusal']['tp']}, FP={run1['refusal']['fp']}, FN={run1['refusal']['fn']}, TN={run1['refusal']['tn']}")
print(f"  Run2: TP={run2['refusal']['tp']}, FP={run2['refusal']['fp']}, FN={run2['refusal']['fn']}, TN={run2['refusal']['tn']}")
print()

print("Failure Taxonomy:")
run1_failures = run1['failure_taxonomy']
run2_failures = run2['failure_taxonomy']
for label in set(list(run1_failures.keys()) + list(run2_failures.keys())):
    if label == 'TOTAL FAILURES':
        continue
    c1 = run1_failures.get(label, 0)
    c2 = run2_failures.get(label, 0)
    diff = abs(c1 - c2)
    marker = " ✓" if diff == 0 else f" ± {diff}"
    print(f"  {label:25} Run1={c1:2d}, Run2={c2:2d}{marker}")

print()
print(f"Total Failures:")
print(f"  Run1: {run1['failures_total']}")
print(f"  Run2: {run2['failures_total']}")
print(f"  Difference: {abs(run1['failures_total'] - run2['failures_total'])}")
print()

print("Retrieval:")
print(f"  Recall@10:")
print(f"    Run1: {run1['retrieval']['recall_at_10']:.4f}")
print(f"    Run2: {run2['retrieval']['recall_at_10']:.4f}")
print(f"    Difference: {abs(run1['retrieval']['recall_at_10'] - run2['retrieval']['recall_at_10']):.4f}")
print()

print("Citation Precision:")
print(f"  Run1: {run1['citation']['mean_precision']:.4f}")
print(f"  Run2: {run2['citation']['mean_precision']:.4f}")
print(f"  Difference: {abs(run1['citation']['mean_precision'] - run2['citation']['mean_precision']):.4f}")
print()

print("Latency:")
print(f"  p50:")
print(f"    Run1: {run1['latency_ms']['p50']}ms")
print(f"    Run2: {run2['latency_ms']['p50']}ms")
print(f"    Difference: {abs(run1['latency_ms']['p50'] - run2['latency_ms']['p50'])}ms")
print()

# Find questions that differed
print("=" * 80)
print("QUESTION-LEVEL DIFFERENCES")
print("=" * 80)

rows1_by_id = {row['id']: row for row in run1['rows']}
rows2_by_id = {row['id']: row for row in run2['rows']}

differences = []
for qid in rows1_by_id:
    r1 = rows1_by_id[qid]
    r2 = rows2_by_id[qid]
    
    if r1.get('refusal_correct') != r2.get('refusal_correct'):
        differences.append({
            'id': qid,
            'type': 'refusal_correct',
            'run1': r1.get('refusal_correct'),
            'run2': r2.get('refusal_correct'),
            'status1': r1.get('status'),
            'status2': r2.get('status'),
        })
    
    if r1.get('answer_correct') != r2.get('answer_correct'):
        differences.append({
            'id': qid,
            'type': 'answer_correct',
            'run1': r1.get('answer_correct'),
            'run2': r2.get('answer_correct'),
        })

if differences:
    print(f"\nFound {len(differences)} question-level differences:")
    for diff in differences:
        print(f"  {diff['id']}: {diff['type']}")
        print(f"    Run1: {diff.get('run1')}")
        print(f"    Run2: {diff.get('run2')}")
        if 'status1' in diff:
            print(f"    Status1: {diff['status1']}, Status2: {diff['status2']}")
else:
    print("\n✓ No question-level differences - perfect reproducibility!")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
total_diffs = sum([
    abs(run1['answer']['correct']['successes'] - run2['answer']['correct']['successes']),
    abs(run1['failures_total'] - run2['failures_total'])
])
if total_diffs == 0:
    print("✓ Perfect reproducibility at temperature=0")
else:
    print(f"⚠ {total_diffs} total differences between runs")
    print("  This is expected with LLM variance even at temperature=0")
