# Evaluation Quick Start

Quick reference for running evaluations and analysis. See `docs/evaluation-workflow.md` for full details.

## Prerequisites

```bash
# Ensure Ollama is running with the model
ollama serve &
ollama pull qwen2.5-coder:7b

# Ensure eval database is ingested
cd backend
python -m app.cli ingest ../data/synthetic
```

## Phase 2: Oracle Run (Measure Retrieval vs Generation Gap)

```bash
cd backend

# Run both modes on dev set (~30-45 min with local model)
python scripts_phase3/eval_v2.py --mode both --dataset dev --label dev-baseline

# Analyze the gap
python scripts_phase3/analyze_oracle_gap.py --dev --label dev-baseline

# Output: docs/results/oracle-gap-dev.md with interpretation
```

## Phase 3: Over-Refusal Analysis

```bash
cd backend

# Analyze false refusals on dev set
python scripts_phase3/analyze_over_refusal.py --dev --output ../docs/results/over-refusal.md --label dev-baseline

# Output: table of all false refusals with diagnostic info
# STOP and review before making changes
```

## Phase 4: Apply Fix and Validate

```bash
cd backend

# After implementing a fix, re-run dev evaluation
python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-after-fix-1

# Compare statistically
python scripts_phase3/paired_bootstrap.py \\
    --before data/evaluation/v2/dev-baseline_dev_current_qwen2.5-coder-7b.json \\
    --after data/evaluation/v2/dev-after-fix-1_dev_current_qwen2.5-coder-7b.json \\
    --metric refusal.false_refusal

# Keep fix only if:
# - False refusals drop by ≥2 with 95% confidence
# - No increase in false answers on unanswerable questions
```

## Phase 5: Model Comparison

```bash
cd backend

# Test different models on dev set
LLM_MODEL=qwen2.5:7b-instruct python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-instruct
LLM_MODEL=qwen2.5-coder:7b python scripts_phase3/eval_v2.py --mode current --dataset dev --label dev-coder

# Compare
python scripts_phase3/paired_bootstrap.py \\
    --before data/evaluation/v2/dev-coder_dev_current_qwen2.5-coder-7b.json \\
    --after data/evaluation/v2/dev-instruct_dev_current_qwen2.5-7b-instruct.json \\
    --metric answer.correct
```

## Phase 9: Final Held-Out Run

```bash
cd backend

# After all fixes are validated on dev, run held-out ONCE
python scripts_phase3/eval_v2.py --mode current --dataset held-out --label final-held-out

# Results in: data/evaluation/v2/final-held-out_held-out_current_qwen2.5-coder-7b.json
```

## File Locations

| File | Purpose |
|------|---------|
| `data/evaluation/v2/questions_dev.json` | 90 dev questions (for tuning) |
| `data/evaluation/v2/questions_held_out.json` | 40 held-out questions (frozen, final validation only) |
| `data/evaluation/v2/split.json` | Split metadata |
| `data/evaluation/v2/{label}_{dataset}_{mode}_{model}.json` | Evaluation results |
| `docs/results/oracle-gap-dev.md` | Oracle analysis output |
| `docs/results/over-refusal.md` | False refusal diagnostic table |

## Common Metrics

| Metric Path | Description |
|-------------|-------------|
| `answer.correct` | Answer correctness (facts matched) |
| `refusal.false_refusal` | Answerable questions refused |
| `refusal.precision` | Refusal precision (TP / (TP + FP)) |
| `citation.precision` | Citation precision |
| `latency_ms` | End-to-end latency |

## Troubleshooting

**Ollama connection errors**: Ensure `ollama serve` is running on port 11434

**Evaluation timeout**: Expected for 90-question dev set (~30-45 min). Run in background:
```bash
nohup python scripts_phase3/eval_v2.py --mode both --dataset dev --label dev-baseline > eval.log 2>&1 &
tail -f eval.log
```

**Missing eval database**: Ingest synthetic corpus first:
```bash
cd backend
python -m app.cli ingest ../data/synthetic
```
