#!/usr/bin/env python3
"""
Create a stratified dev/held-out split of the v2 question set.

Requirements:
- 90 dev, 40 held-out
- Stratified by category
- At least 8 unanswerable questions in held-out
- Reproducible (fixed random seed)
"""
import json
import random
from pathlib import Path
from collections import Counter

def main():
    # Load questions
    repo_root = Path(__file__).parent.parent.parent
    questions_path = repo_root / "data/evaluation/v2/questions.json"
    with open(questions_path) as f:
        data = json.load(f)
    
    questions = data["questions"]
    print(f"Total questions: {len(questions)}")
    
    # Group by category
    by_category = {}
    for q in questions:
        cat = q["category"]
        by_category.setdefault(cat, []).append(q)
    
    print("\nCategory distribution:")
    for cat, qs in sorted(by_category.items()):
        unanswerable_count = sum(1 for q in qs if q.get("expected_refusal"))
        print(f"  {cat}: {len(qs)} ({unanswerable_count} unanswerable)")
    
    # Count total unanswerable
    total_unanswerable = sum(1 for q in questions if q.get("expected_refusal"))
    print(f"\nTotal unanswerable: {total_unanswerable}")
    
    # Target: 40 held-out, proportional split per category, >=8 unanswerable in held-out
    held_out_target = 40
    dev_target = len(questions) - held_out_target
    
    # Calculate held-out proportion
    held_out_proportion = held_out_target / len(questions)
    
    # For reproducibility
    random.seed(42)
    
    # First, ensure we get at least 8 unanswerable in held-out
    # Separate unanswerable and answerable
    unanswerable = [q for q in questions if q.get("expected_refusal")]
    answerable = [q for q in questions if not q.get("expected_refusal")]
    
    print(f"\nAnswerable: {len(answerable)}, Unanswerable: {len(unanswerable)}")
    
    # Group unanswerable by category for stratification
    unans_by_cat = {}
    for q in unanswerable:
        unans_by_cat.setdefault(q["category"], []).append(q)
    
    ans_by_cat = {}
    for q in answerable:
        ans_by_cat.setdefault(q["category"], []).append(q)
    
    # Allocate held-out unanswerable: aim for ~31% (8 out of 26)
    # to match overall proportion but ensure >= 8
    held_out_unans_target = max(8, int(len(unanswerable) * held_out_proportion))
    held_out_unans = []
    dev_unans = []
    
    # Stratified sampling of unanswerable
    for cat, qs in unans_by_cat.items():
        random.shuffle(qs)
        cat_held_out_count = max(1, int(len(qs) * held_out_proportion))
        held_out_unans.extend(qs[:cat_held_out_count])
        dev_unans.extend(qs[cat_held_out_count:])
    
    # Ensure we have at least 8 unanswerable in held-out
    while len(held_out_unans) < 8 and dev_unans:
        held_out_unans.append(dev_unans.pop())
    
    print(f"\nHeld-out unanswerable: {len(held_out_unans)}")
    print(f"Dev unanswerable: {len(dev_unans)}")
    
    # Now allocate answerable questions to reach targets
    remaining_held_out_slots = held_out_target - len(held_out_unans)
    held_out_ans = []
    dev_ans = []
    
    # Stratified sampling of answerable
    for cat, qs in ans_by_cat.items():
        random.shuffle(qs)
        cat_held_out_count = max(1, int(len(qs) * held_out_proportion))
        held_out_ans.extend(qs[:cat_held_out_count])
        dev_ans.extend(qs[cat_held_out_count:])
    
    # Adjust to hit exact target
    if len(held_out_ans) > remaining_held_out_slots:
        # Move excess to dev
        excess = len(held_out_ans) - remaining_held_out_slots
        random.shuffle(held_out_ans)
        dev_ans.extend(held_out_ans[-excess:])
        held_out_ans = held_out_ans[:-excess]
    elif len(held_out_ans) < remaining_held_out_slots:
        # Move from dev to held-out
        shortage = remaining_held_out_slots - len(held_out_ans)
        random.shuffle(dev_ans)
        held_out_ans.extend(dev_ans[:shortage])
        dev_ans = dev_ans[shortage:]
    
    # Combine
    held_out = held_out_unans + held_out_ans
    dev = dev_unans + dev_ans
    
    # Sort by ID for readability
    held_out.sort(key=lambda q: q["id"])
    dev.sort(key=lambda q: q["id"])
    
    print(f"\nFinal split:")
    print(f"  Dev: {len(dev)} ({sum(1 for q in dev if q.get('expected_refusal'))} unanswerable)")
    print(f"  Held-out: {len(held_out)} ({sum(1 for q in held_out if q.get('expected_refusal'))} unanswerable)")
    
    # Show category distribution
    print("\nDev category distribution:")
    dev_cats = Counter(q["category"] for q in dev)
    for cat, count in sorted(dev_cats.items()):
        unans = sum(1 for q in dev if q["category"] == cat and q.get("expected_refusal"))
        print(f"  {cat}: {count} ({unans} unanswerable)")
    
    print("\nHeld-out category distribution:")
    held_out_cats = Counter(q["category"] for q in held_out)
    for cat, count in sorted(held_out_cats.items()):
        unans = sum(1 for q in held_out if q["category"] == cat and q.get("expected_refusal"))
        print(f"  {cat}: {count} ({unans} unanswerable)")
    
    # Create split file
    split_data = {
        "name": "epi-golden-v2-split",
        "version": "1.0.0",
        "created": "2026-11-03",
        "description": "Stratified dev/held-out split of v2 questions. Held-out set is frozen; do not tune against it.",
        "seed": 42,
        "dev_count": len(dev),
        "held_out_count": len(held_out),
        "dev": [q["id"] for q in dev],
        "held_out": [q["id"] for q in held_out]
    }
    
    split_path = repo_root / "data/evaluation/v2/split.json"
    with open(split_path, "w") as f:
        json.dump(split_data, f, indent=2)
    
    print(f"\nSplit written to {split_path}")
    
    # Also create full question files for convenience
    dev_data = dict(data)
    dev_data["name"] = "epi-golden-v2-dev"
    dev_data["questions"] = dev
    
    held_out_data = dict(data)
    held_out_data["name"] = "epi-golden-v2-held-out"
    held_out_data["questions"] = held_out
    held_out_data["note"] = "FROZEN HELD-OUT SET - Do not read failures or tune against this set"
    
    dev_path = repo_root / "data/evaluation/v2/questions_dev.json"
    held_out_path = repo_root / "data/evaluation/v2/questions_held_out.json"
    
    with open(dev_path, "w") as f:
        json.dump(dev_data, f, indent=2)
    
    with open(held_out_path, "w") as f:
        json.dump(held_out_data, f, indent=2)
    
    print(f"Dev questions written to {dev_path}")
    print(f"Held-out questions written to {held_out_path}")

if __name__ == "__main__":
    main()
