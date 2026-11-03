#!/usr/bin/env python3
"""Generate cross-tab of failures: expected doc retrieved × fixed by oracle."""
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load baseline results
with open(PROJECT_ROOT / 'data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json') as f:
    baseline = json.load(f)

# Load oracle results
with open(PROJECT_ROOT / 'data/evaluation/v2/dev-baseline_dev_oracle_qwen2.5-coder-7b.json') as f:
    oracle = json.load(f)

# Load questions
with open(PROJECT_ROOT / 'data/evaluation/v2/questions_dev.json') as f:
    questions_data = json.load(f)

questions_by_id = {q['id']: q for q in questions_data['questions']}
baseline_by_id = {r['id']: r for r in baseline['rows']}
oracle_by_id = {r['id']: r for r in oracle['rows']}

# Find all failures in baseline
failures = []
for row in baseline['rows']:
    q = questions_by_id[row['id']]
    expected_refusal = q.get('expected_refusal', False)
    answer_correct = row.get('answer_correct', False)
    refused = row.get('refused', False)
    
    # Check if failure
    is_failure = False
    failure_type = None
    
    if expected_refusal:
        if not refused:
            is_failure = True
            failure_type = "under_refusal"
    else:
        if not answer_correct or refused:
            is_failure = True
            if refused:
                failure_type = "false_refusal"
            else:
                failure_type = "wrong_answer"
    
    if not is_failure:
        continue
    
    # Check if expected doc in top-10
    expected_docs = set(q.get('expected_documents', []))
    retrieved = row.get('retrieved_documents', [])[:10]
    expected_in_top10 = bool(expected_docs & set(retrieved)) if expected_docs else None
    
    # Check if oracle fixed it
    oracle_row = oracle_by_id[row['id']]
    oracle_answer_correct = oracle_row.get('answer_correct', False)
    oracle_refused = oracle_row.get('refused', False)
    
    if expected_refusal:
        fixed_by_oracle = oracle_refused if not refused else None
    else:
        if refused:
            # False refusal - fixed if oracle answered correctly
            fixed_by_oracle = oracle_answer_correct and not oracle_refused
        else:
            # Wrong answer - fixed if oracle got it right
            fixed_by_oracle = oracle_answer_correct
    
    # Check which component refused (for false refusals)
    refusal_check = None
    if failure_type == "false_refusal":
        status = row.get('status', '')
        # Use answerability field
        answerability = row.get('answerability', '')
        if isinstance(answerability, str):
            answerability_str = answerability.lower()
        elif isinstance(answerability, dict):
            answerability_str = str(answerability.get('level', '')).lower()
        else:
            answerability_str = ''
        
        if 'coverage' in answerability_str or 'low_coverage' in answerability_str:
            refusal_check = 'coverage'
        elif 'grounding' in answerability_str or 'weak_grounding' in answerability_str:
            refusal_check = 'grounding'
        elif 'claim' in answerability_str:
            refusal_check = 'claim_binding'
        else:
            refusal_check = 'answerability_other'
    
    # Check if oracle provided chunks for expected document
    oracle_retrieved = set(oracle_row.get('retrieved_documents', []))
    oracle_supplied_expected = bool(expected_docs & oracle_retrieved) if expected_docs else None
    
    failures.append({
        'id': row['id'],
        'category': q.get('category', ''),
        'failure_type': failure_type,
        'expected_in_top10': expected_in_top10,
        'fixed_by_oracle': fixed_by_oracle,
        'oracle_supplied_expected': oracle_supplied_expected,
        'refusal_check': refusal_check,
    })

# Print table
print(f"Total failures: {len(failures)}")
print()
print("| ID | Category | Failure Type | Expected in Top-10 | Fixed by Oracle | Oracle Supplied Expected | Refusal Check |")
print("|----|----------|--------------|-------------------|----------------|-------------------------|---------------|")

for f in sorted(failures, key=lambda x: (x['failure_type'], x['id'])):
    exp_top10 = "yes" if f['expected_in_top10'] else "no" if f['expected_in_top10'] is False else "n/a"
    fixed = "yes" if f['fixed_by_oracle'] else "no" if f['fixed_by_oracle'] is False else "n/a"
    oracle_supplied = "yes" if f['oracle_supplied_expected'] else "no" if f['oracle_supplied_expected'] is False else "n/a"
    refusal_check = f['refusal_check'] or "n/a"
    
    print(f"| {f['id']} | {f['category']} | {f['failure_type']} | {exp_top10} | {fixed} | {oracle_supplied} | {refusal_check} |")

# 2x2 count
print()
print("2x2 Cross-tab: [Expected Doc in Top-10] × [Fixed by Oracle]")
print()

# Filter to only questions with expected_documents (exclude n/a)
with_expected = [f for f in failures if f['expected_in_top10'] is not None]

# Count false refusals separately
false_refusals = [f for f in failures if f['failure_type'] == 'false_refusal']
print(f"False refusals: {len(false_refusals)}")

# Cross-tab for all failures with expected docs
yes_yes = sum(1 for f in with_expected if f['expected_in_top10'] and f['fixed_by_oracle'])
yes_no = sum(1 for f in with_expected if f['expected_in_top10'] and not f['fixed_by_oracle'])
no_yes = sum(1 for f in with_expected if not f['expected_in_top10'] and f['fixed_by_oracle'])
no_no = sum(1 for f in with_expected if not f['expected_in_top10'] and not f['fixed_by_oracle'])

print()
print("|                          | Fixed by Oracle | Not Fixed by Oracle | Total |")
print("|--------------------------|-----------------|---------------------|-------|")
print(f"| Expected Doc in Top-10   | {yes_yes:15} | {yes_no:19} | {yes_yes + yes_no:5} |")
print(f"| Expected Doc NOT in Top-10| {no_yes:15} | {no_no:19} | {no_yes + no_no:5} |")
print(f"| **Total**                | **{yes_yes + no_yes:13}** | **{yes_no + no_no:17}** | **{len(with_expected):3}** |")

print()
print(f"Questions without expected_documents field: {len(failures) - len(with_expected)}")
