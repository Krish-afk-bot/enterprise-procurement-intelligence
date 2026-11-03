#!/usr/bin/env python3
"""Quick script to verify failure counts."""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

with open(PROJECT_ROOT / 'data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json') as f:
    results = json.load(f)

with open(PROJECT_ROOT / 'data/evaluation/v2/questions_dev.json') as f:
    questions_data = json.load(f)

questions_by_id = {q['id']: q for q in questions_data['questions']}

answerable = []
unanswerable = []

for row in results['rows']:
    q = questions_by_id[row['id']]
    if q.get('expected_refusal', False):
        unanswerable.append(row)
    else:
        answerable.append(row)

print(f'Total questions: {len(results["rows"])}')
print(f'Answerable: {len(answerable)}')
print(f'Unanswerable: {len(unanswerable)}')
print()

# Answerable stats - use answer_correct
answerable_correct = sum(1 for r in answerable if r.get('answer_correct', False))
answerable_refused = sum(1 for r in answerable if r.get('refused', False))
print(f'Answerable correct: {answerable_correct} ({100*answerable_correct/len(answerable):.1f}%)')
print(f'Answerable refused (FP): {answerable_refused}')
print(f'Answerable failures: {len(answerable) - answerable_correct}')
print()

# Unanswerable stats
unanswerable_refused = sum(1 for r in unanswerable if r.get('refused', False))
unanswerable_answered = len(unanswerable) - unanswerable_refused
print(f'Unanswerable correctly refused: {unanswerable_refused}')
print(f'Unanswerable incorrectly answered (FN): {unanswerable_answered}')
