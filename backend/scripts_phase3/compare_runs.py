#!/usr/bin/env python3
"""Compare two evaluation runs and list changed questions."""
import json
from pathlib import Path

def compare_runs(baseline_path: Path, experiment_path: Path):
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(experiment_path) as f:
        experiment = json.load(f)
    
    baseline_rows = {row['id']: row for row in baseline['rows']}
    experiment_rows = {row['id']: row for row in experiment['rows']}
    
    # Count correct
    baseline_correct = sum(1 for row in baseline['rows'] if row.get('answer_correct'))
    experiment_correct = sum(1 for row in experiment['rows'] if row.get('answer_correct'))
    
    print(f"Baseline: {baseline_correct}/{len(baseline['rows'])} correct")
    print(f"Experiment A: {experiment_correct}/{len(experiment['rows'])} correct")
    print(f"Difference: +{experiment_correct - baseline_correct}")
    
    # False refusals
    baseline_false_refusals = []
    experiment_false_refusals = []
    
    for q_id in baseline_rows:
        b_row = baseline_rows[q_id]
        e_row = experiment_rows.get(q_id, {})
        
        b_expected_refusal = b_row.get('expected_refusal', False)
        e_expected_refusal = e_row.get('expected_refusal', False)
        
        b_status = b_row.get('status', '')
        e_status = e_row.get('status', '')
        
        if not b_expected_refusal and b_status in ('insufficient_evidence', 'refused'):
            baseline_false_refusals.append(q_id)
        
        if not e_expected_refusal and e_status in ('insufficient_evidence', 'refused'):
            experiment_false_refusals.append(q_id)
    
    print(f"\nFalse refusals:")
    print(f"Baseline: {len(baseline_false_refusals)}")
    print(f"Experiment A: {len(experiment_false_refusals)}")
    
    # Changed questions
    changed = []
    for q_id in baseline_rows:
        b_row = baseline_rows[q_id]
        e_row = experiment_rows.get(q_id, {})
        
        b_correct = b_row.get('answer_correct', False)
        e_correct = e_row.get('answer_correct', False)
        
        if b_correct != e_correct:
            changed.append({
                'id': q_id,
                'baseline': b_correct,
                'experiment': e_correct,
                'baseline_status': b_row.get('status', ''),
                'experiment_status': e_row.get('status', ''),
                'failure_label': e_row.get('failure_label', b_row.get('failure_label', '')),
            })
    
    print(f"\n=== Changed questions: {len(changed)} ===")
    for item in changed:
        direction = "✓ FIXED" if item['experiment'] else "✗ BROKE"
        print(f"{direction:8} {item['id']:15} baseline={item['baseline']:5} exp_a={item['experiment']:5}  "
              f"{item['baseline_status']:25} -> {item['experiment_status']:25}  "
              f"{item['failure_label']}")
    
    # Retrieval metrics
    baseline_recall_10 = sum(row.get('recall_at_10') or 0 for row in baseline['rows']) / len(baseline['rows'])
    experiment_recall_10 = sum(row.get('recall_at_10') or 0 for row in experiment['rows']) / len(experiment['rows'])
    
    baseline_mrr = sum(row.get('reciprocal_rank') or 0 for row in baseline['rows']) / len(baseline['rows'])
    experiment_mrr = sum(row.get('reciprocal_rank') or 0 for row in experiment['rows']) / len(experiment['rows'])
    
    print(f"\n=== Retrieval Metrics ===")
    print(f"Recall@10:  baseline={baseline_recall_10:.4f}  exp_a={experiment_recall_10:.4f}  diff={experiment_recall_10-baseline_recall_10:+.4f}")
    print(f"MRR:        baseline={baseline_mrr:.4f}  exp_a={experiment_mrr:.4f}  diff={experiment_mrr-baseline_mrr:+.4f}")

if __name__ == '__main__':
    baseline_path = Path('../data/evaluation/v2/dev-ocr-baseline-run1_dev_current_qwen2.5-coder-7b.json')
    experiment_path = Path('../data/evaluation/v2/dev-experiment-a_dev_current_qwen2.5-coder-7b.json')
    compare_runs(baseline_path, experiment_path)
