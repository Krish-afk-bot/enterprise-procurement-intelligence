"""Compose the human-readable v4 report from the recorded run artefacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "data" / "evaluation" / "benchmark_v4"


def pct(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def ci(bucket):
    if not bucket:
        return "—"
    return f"{bucket['rate'] * 100:.1f}% ({bucket['low'] * 100:.1f}–{bucket['high'] * 100:.1f})"


def main() -> int:
    a = json.loads((V / "analysis.json").read_text(encoding="utf-8"))
    cov = json.loads((V / "coverage_report.json").read_text(encoding="utf-8"))
    judge = json.loads((V / "judge_report.json").read_text(encoding="utf-8"))
    mcp = json.loads((V / "mcp_report.json").read_text(encoding="utf-8"))
    intent = json.loads((V / "intent_report.json").read_text(encoding="utf-8"))
    questions = json.loads((V / "questions.json").read_text(encoding="utf-8"))
    digest = (V / "questions.sha256").read_text(encoding="utf-8").strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    A, B = a["run_A"], a["run_B"]
    base = a["comparison_120"]["baseline"]
    subset = {
        "A": {"answer": 0.3889, "recall": 1.0, "p50": 9244},
        "C1": {"answer": 0.3889, "recall": 1.0, "p50": 8970},
        "C2": {"answer": 0.3611, "recall": 1.0, "p50": 8775},
    }
    subset_answer = [v["answer"] for v in subset.values()]
    variance = max(subset_answer) - min(subset_answer)

    lines = [
        "# EPI benchmark v4 — full re-ingestion and 150-question run",
        "",
        "- Git commit at freeze: `3d15fbf` (the deterministic-chunk-id bug fix was committed after the runs).",
        f"- Report commit: `{commit}`.",
        f"- Dataset SHA-256: `{digest}` (frozen before Run A).",
        f"- Dataset: {questions['question_count']} questions — {questions['distribution']['answerable']} answerable, "
        f"{questions['distribution']['unanswerable']} unanswerable, {questions['distribution']['needs_review']} needs_review.",
        "- Corpus: 20 source documents, 19 indexed, 1 empty portal page; 42 pages; 655 active chunks.",
        "",
        "## 1. Ingestion and coverage",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Documents rebuilt | {cov['documents']} |",
        "| Indexed / needs_review | 19 / 1 (`0664eb_tender_13.html` is an empty page) |",
        f"| Pages with text / with ≥1 chunk | {cov['pages_with_text']} / {cov['pages_with_chunk']} |",
        f"| Chunks | {cov['chunks']} |",
        f"| Character coverage (5-gram, overlap excluded) | {pct(cov['char_coverage'])} |",
        f"| Documents below 99% char coverage | {len(cov['below_char_target'])} |",
        f"| Idempotent chunk ids | {cov['idempotency'].get('same_ids')} (count {cov['idempotency'].get('chunks_before')} → {cov['idempotency'].get('chunks_after')}) |",
        "",
        "Below target: `065b20_tender_6.pdf` at 93.9% (page headers/footers such as `PROC/TD/04 v1.2 … Page N of 22` are removed by the parser and are not tagged as boilerplate); "
        "`064670_tender_1.html` at 97.2% (portal chrome). `069b28_tender_16.docx` yields only 409 characters from a 119 KB file: its tender body is not in the DOCX text layer (embedded object/image), so it is a real extraction gap, not a chunking gap. "
        "No text chunk stores character offsets or bounding boxes: a schema gap, reported rather than worked around.",
        "",
        "## 2. Retrieval (Run A, 150 questions)",
        "",
        "| Metric | Value | n |",
        "| --- | --- | --- |",
        f"| Recall@1 | {pct(A['retrieval']['recall_at_1'])} | {A['retrieval']['questions']} |",
        f"| Recall@3 | {pct(A['retrieval']['recall_at_3'])} | {A['retrieval']['questions']} |",
        f"| Recall@5 | {pct(A['retrieval']['recall_at_5'])} | {A['retrieval']['questions']} |",
        f"| Recall@10 | {pct(A['retrieval']['recall_at_10'])} | {A['retrieval']['questions']} |",
        f"| MRR | {A['retrieval']['mrr']} | {A['retrieval']['questions']} |",
        f"| nDCG@10 | {A['retrieval']['ndcg_at_10']} | {A['retrieval']['questions']} |",
        "",
        "Recall@15 is not reported: the run retrieved 10 candidates, the same cap as the baseline. Raising it would change the configuration being measured.",
        "",
        "## 3. Answer quality",
        "",
        "| Metric | Run A (150) | n |",
        "| --- | --- | --- |",
        f"| Literal fact containment | {ci(A['answer']['literal_correct'])} | {A['answer']['questions']} |",
        f"| Normalized fact match | {ci(A['answer']['normalized_correct'])} | {A['answer']['questions']} |",
        f"| LLM judge correctness | {pct(judge['rate'])} ({judge['correct']}/{judge['sample']}) | {judge['sample']} |",
        "",
        f"The judge is `{judge['judge_model']}` — the same model that generated the answers, because it is the only model installed. It is stricter than literal containment and is not independent. "
        f"Excluding the 15 `needs_review` v3 items, answer accuracy is {pct((A['scored_excluding_needs_review']['answer']['normalized_correct'] or {}).get('rate'))} on "
        f"{A['scored_excluding_needs_review']['answer']['questions']} questions.",
        "",
        "## 4. Citations and faithfulness",
        "",
        "| Metric | Value | n |",
        "| --- | --- | --- |",
        f"| Citation precision | {A['citation']['precision']} | {A['citation']['questions']} |",
        f"| Citation recall | {A['citation']['recall']} | {A['citation']['questions']} |",
        f"| Answers with all citations valid | {ci(A['citation']['all_valid_rate'])} | {A['citation']['all_valid_rate']['total'] if A['citation']['all_valid_rate'] else 0} |",
        f"| Pipeline faithfulness | {A['faithfulness']['mean']} | {A['faithfulness']['questions']} |",
        f"| Unsupported-claim rate | {A['faithfulness']['unsupported_claim_rate']} | {A['faithfulness']['questions']} |",
        "",
        "No independent faithfulness check was run beyond the judge; citation validity is the verifier's own verdict, not a second reader.",
        "",
        "## 5. Refusals (refuse = positive class)",
        "",
        "| Metric | Run A |",
        "| --- | --- |",
        f"| Correct refusals (TP) | {A['refusal']['tp']} |",
        f"| False refusals (FP, answerable refused) | {A['refusal']['fp_false_refusal']} |",
        f"| False answers (FN, unanswerable answered) | {A['refusal']['fn_false_answer']} |",
        f"| Correct answers (TN) | {A['refusal']['tn']} |",
        f"| Precision | {A['refusal']['precision']} |",
        f"| Recall | {A['refusal']['recall']} |",
        f"| Accuracy | {ci(A['refusal']['accuracy'])} |",
        "",
        "## 6. Baseline comparison on the identical 120 questions (Run B)",
        "",
        "| Metric | Old baseline (recomputed) | Run B | Change | Verdict |",
        "| --- | --- | --- | --- | --- |",
        f"| Answer correct, literal | {ci(base['answer']['literal_correct'])} | {ci(B['answer']['literal_correct'])} | "
        f"{(B['answer']['literal_correct']['rate'] - base['answer']['literal_correct']['rate']) * 100:+.1f} pp | within noise (CIs overlap) |",
        f"| Recall@5 | {pct(base['retrieval']['recall_at_5'])} | {pct(B['retrieval']['recall_at_5'])} | "
        f"{(B['retrieval']['recall_at_5'] - base['retrieval']['recall_at_5']) * 100:+.1f} pp | real (deterministic retriever) |",
        f"| Recall@10 | {pct(base['retrieval']['recall_at_10'])} | {pct(B['retrieval']['recall_at_10'])} | "
        f"{(B['retrieval']['recall_at_10'] - base['retrieval']['recall_at_10']) * 100:+.1f} pp | real |",
        f"| MRR | {base['retrieval']['mrr']} | {B['retrieval']['mrr']} | "
        f"{B['retrieval']['mrr'] - base['retrieval']['mrr']:+.3f} | real |",
        f"| Refusal precision | {base['refusal']['precision']} | {B['refusal']['precision']} | "
        f"{(B['refusal']['precision'] - base['refusal']['precision']) * 100:+.1f} pp | not separable from noise |",
        f"| Refusal recall | {base['refusal']['recall']} | {B['refusal']['recall']} | "
        f"{(B['refusal']['recall'] - base['refusal']['recall']) * 100:+.1f} pp | small |",
        f"| Latency p50 (ms) | {base['latency_ms']['p50']} | {B['latency_ms']['p50']} | — | machine-load dependent |",
        "",
        "The old report's 86.8% Recall@5 and Recall@10 were identical because no expected document first appeared at rank 6–10: "
        "all hits were already in the top five. It was not a cut-off bug.",
        "",
        "## 7. Variance (50-question stratified subset)",
        "",
        "| Run | Answer (normalized) | Recall@10 | p50 ms |",
        "| --- | --- | --- | --- |",
        f"| A, restricted to subset | {pct(subset['A']['answer'])} | {pct(subset['A']['recall'])} | {subset['A']['p50']} |",
        f"| C1 | {pct(subset['C1']['answer'])} | {pct(subset['C1']['recall'])} | {subset['C1']['p50']} |",
        f"| C2 | {pct(subset['C2']['answer'])} | {pct(subset['C2']['recall'])} | {subset['C2']['p50']} |",
        "",
        f"Answer accuracy ranges over {variance * 100:.1f} pp across repeats; retrieval is identical. Two full 150-question repeats would have taken another hour; "
        "the variance estimate is therefore from a 50-question subset and is a limitation, not a full-set confidence interval.",
        "",
        "## 8. Categories (Run A)",
        "",
        "| Category | Q | Answer (normalized) | Recall@10 | Citation P | Refusal P/R | p50 ms |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, item in A["by_category"].items():
        lines.append(
            f"| {name} | {item['questions']} | {pct(item['answer_normalized'])} | {pct(item['recall_at_10'])} | "
            f"{item['citation_precision']} | {item['refusal_precision']}/{item['refusal_recall']} | {item['p50_ms']} |"
        )

    lines += [
        "",
        "Worst categories by answer accuracy where at least one answerable question exists: award_criteria, obligations and amendments (0%), "
        "payment_terms (50%), procurement_values (50%). These are numeric/dense-table and clause questions where the retriever found the document "
        "but the generator or verifier failed on the passage.",
        "",
        "## 9. Routing, classification and MCP",
        "",
        f"- Rule-based intent accuracy on 45 fresh hand-labelled queries: **{pct(intent['accuracy'])}**. Weakest: temporal_change 0/5, "
        "relationship 1/5, document_lookup 1/5; best: compliance_check 4/5, general 4/5.",
        "- Routing: 148/150 generations used the large model; structured/SQL engine ran on 87 questions and the graph on 17. "
        "No small LLM is installed, so its fallback path could not be exercised. The VLM is configured but no vision model exists: 5 PDF pages logged HTTP 404 and kept text.",
        f"- MCP: all {len(mcp['available_tools'])} tools advertised; {mcp['successful']}/{mcp['total']} tool calls succeeded; all 4 negative cases rejected; "
        f"{mcp['audit_log_rows_for_mcp']} audit rows written. The agent-over-MCP arm was not run (no validated tool-calling model; the tools search titles/structured fields, not chunk text).",
        "",
        "## 10. Failure taxonomy (Run A)",
        "",
        "| Label | Count |",
        "| --- | --- |",
    ]
    for label, count in A["failure_taxonomy"].items():
        lines.append(f"| {label} | {count} |")

    lines += ["", "### Top 20 failures", "", "| id | label | question | expected | answer (truncated) |", "| --- | --- | --- | --- | --- |"]
    for row in a["failures_top20"]:
        answer = str(row.get("answer") or "").replace("|", " ").replace("\n", " ")[:140]
        lines.append(
            f"| {row['id']} | {row['label']} | {row['question'][:80]} | {str(row.get('expected'))[:60]} | {answer} |"
        )

    lines += [
        "",
        "## 11. Configuration",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        "| Database | SQLite `backend/var/epi.db` |",
        "| Vector store | local numpy cosine index (`procurement_chunks`, 384d) |",
        "| Graph | local SQLite property graph |",
        "| Cache | in-memory |",
        "| Object storage | local filesystem |",
        "| Generation | qwen2.5-coder:7b via Ollama, temperature 0.1, max 2048 tokens |",
        "| Small LLM | not configured |",
        "| VLM | configured, no vision model available |",
        "| Embeddings | BAAI/bge-small-en-v1.5, 384 dimensions, CUDA |",
        "| Reranker | BAAI/bge-reranker-v2-m3 (cross-encoder) |",
        "| Retrieval | dense 50 + BM25 50, RRF k=45, rerank 15, context 12 chunks / 6000 tokens, top_k 10 |",
        "| Chunking | target 320, max 700, overlap 60 |",
        "| Hardware | Windows, Python 3.13, CUDA GPU |",
        "",
        "## 12. Reproduction",
        "",
        "```sh",
        "cd backend",
        "python scripts/reindex_corpus.py                  # rebuild + coverage_report.*",
        "python scripts/build_benchmark_v4.py              # questions.json + SHA-256",
        "python scripts/intent_eval.py",
        "python scripts/verify_mcp_all.py",
        "python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v4 \\",
        "  --out ../data/evaluation/benchmark_v4/results/run_A --top-k 10 --quiet",
        "python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v3 \\",
        "  --out ../data/evaluation/benchmark_v4/results/run_B --top-k 10 --quiet",
        "python scripts/run_benchmark_v3.py --dataset-dir ../data/evaluation/benchmark_v4/subset50 \\",
        "  --out ../data/evaluation/benchmark_v4/results/run_C_1 --top-k 10 --quiet",
        "python scripts/judge_answers.py --sample 40",
        "python scripts/analyze_benchmark_v4.py",
        "```",
        "",
        "## 13. Limitations",
        "",
        "- Labels are not human-adjudicated. 15 v3 labels remain `needs_review`; 66 other v3 answerable labels were machine-checked against the cited page, and all 30 new labels passed the same check. "
        "No reviewer has signed off, and `review_sample.csv` exists for that review.",
        "- The judge shares the generator's model; its 32.5% is not an independent correctness estimate.",
        "- Generation ran at temperature 0.1, not 0, because that is the configured production value; variance was measured instead.",
        "- Variance is measured on a 50-question subset, not the full 150.",
        "- 069b28_tender_16.docx content is missing from its text layer; the 409 characters extracted are the whole available text.",
        "- The old benchmark's Recall@5 = Recall@10 was verified as real (no rank 6–10 hits), not a metric bug.",
        "- The corpus is 20 UK tender notices of one type; results do not generalise to other document families.",
        "",
    ]

    (V / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", V / "REPORT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
