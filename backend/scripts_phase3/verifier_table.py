#!/usr/bin/env python3
"""Generate verifier table for questions where expected doc in top-10 but refused/partial."""
import json
from pathlib import Path

def generate_verifier_table(report_path: Path, questions_path: Path):
    with open(report_path) as f:
        report = json.load(f)
    
    with open(questions_path) as f:
        questions_data = json.load(f)
    
    questions = {q['id']: q for q in questions_data['questions']}
    
    print("=" * 140)
    print(f"{'Question ID':20} {'Status':20} {'Expected Docs':30} {'Retrieved Docs (top-10)':50}")
    print("=" * 140)
    
    count = 0
    for row in report['rows']:
        q_id = row['id']
        status = row.get('status', '')
        
        # Only include refused or partial
        if status not in ('insufficient_evidence', 'refused', 'partial'):
            continue
        
        question = questions.get(q_id, {})
        expected_docs = question.get('expected_documents', [])
        
        if not expected_docs:
            continue
        
        retrieved_docs = row.get('retrieved_documents', [])[:10]
        
        # Check if any expected doc is in top-10
        expected_in_top_10 = any(doc in retrieved_docs for doc in expected_docs)
        
        if expected_in_top_10:
            count += 1
            expected_docs_str = ', '.join(expected_docs[:2]) if len(expected_docs) <= 2 else f"{expected_docs[0]}, +{len(expected_docs)-1}"
            retrieved_docs_str = ', '.join(retrieved_docs[:3]) if len(retrieved_docs) <= 3 else f"{', '.join(retrieved_docs[:2])}, +{len(retrieved_docs)-2}"
            
            print(f"{q_id:20} {status:20} {expected_docs_str:30} {retrieved_docs_str:50}")
    
    print("=" * 140)
    print(f"Total: {count} questions")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python verifier_table.py <label>")
        print("Example: python verifier_table.py dev-experiment-a")
        sys.exit(1)
    
    label = sys.argv[1]
    report_path = Path(f'../data/evaluation/v2/{label}_dev_current_qwen2.5-coder-7b.json')
    questions_path = Path('../data/evaluation/v2/questions.json')
    
    generate_verifier_table(report_path, questions_path)
