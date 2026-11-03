import json

with open('../data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json') as f:
    data = json.load(f)

print('Refusal stats from JSON:')
print(f'  TP (correct refusals): {data["refusal"]["tp"]}')
print(f'  FP (false refusals): {data["refusal"]["fp"]}')
print(f'  FN (under-refusals): {data["refusal"]["fn"]}')
print(f'  TN (correct answers): {data["refusal"]["tn"]}')
print(f'  Total: {sum([data["refusal"][x] for x in ["tp","fp","fn","tn"]])}')

print('\nLooking for FP rows (answerable but refused):')
count = 0
for row in data['rows']:
    if not row.get('expected_refusal', False) and row.get('refused', False):
        count += 1
        status = row.get('status', '')
        print(f"  {row['id']}: status={status}, refused={row['refused']}")

print(f'\nTotal FP found in rows: {count}')
print(f'Matches JSON refusal.fp? {count == data["refusal"]["fp"]}')
