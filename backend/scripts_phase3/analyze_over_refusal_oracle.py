#!/usr/bin/env python3
"""
Quick script to analyze oracle mode over-refusal.
Just change the results file to oracle mode version.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from analyze_over_refusal import analyze_over_refusal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"

results_file = EVAL_DIR / "dev-baseline_dev_oracle_qwen2.5-coder-7b.json"
questions_file = EVAL_DIR / "questions_dev.json"
output_file = PROJECT_ROOT / "docs" / "results" / "over-refusal-oracle-dev.md"

markdown = analyze_over_refusal(results_file, questions_file)
print(markdown)

with open(output_file, "w") as f:
    f.write(markdown)

print(f"\nAnalysis written to {output_file}")
