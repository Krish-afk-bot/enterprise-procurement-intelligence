"""LLM-as-judge correctness on a deterministic sample of Run A answers.

The only model available locally is the generator itself, so this is a same-model
judge: it catches obvious wrong answers and missing facts, but it is not an
independent adjudicator and is reported as such.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config.settings import get_settings  # noqa: E402

PROMPT = """You are grading a procurement question-answering system.
Question: {question}
Reference answer: {expected}
Required facts (all must be present to be correct): {facts}
System answer: {answer}

Is the system answer correct? It is correct only if every required fact is present
(either verbatim or as an unambiguous equivalent number/date/name) and nothing
contradicts the reference. A refusal is incorrect when the question is answerable.
Reply with JSON only: {{"correct": true|false, "reason": "..."}}"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default=str(ROOT.parent / "data" / "evaluation" / "benchmark_v4" / "results" / "run_A"))
    parser.add_argument("--sample", type=int, default=60)
    args = parser.parse_args()
    settings = get_settings()
    rows = [
        json.loads(line)
        for line in (Path(args.run) / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    answerable = [row for row in rows if not row.get("expected_refusal") and row.get("expected_facts")]
    sample = random.Random(20261114).sample(answerable, min(args.sample, len(answerable)))
    verdicts = []
    with httpx.Client(timeout=120) as client:
        for index, row in enumerate(sample, start=1):
            prompt = PROMPT.format(
                question=row["question"],
                expected=row.get("expected_answer"),
                facts=row.get("expected_facts"),
                answer=(row.get("answer_text") or "")[:2500],
            )
            try:
                response = client.post(
                    settings.llm_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key or 'local'}"},
                    json={
                        "model": settings.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0,
                        "max_tokens": 200,
                    },
                )
                response.raise_for_status()
                text = response.json()["choices"][0]["message"]["content"]
                match = re.search(r"\{.*\}", text, re.S)
                parsed = json.loads(match.group(0)) if match else {"correct": False, "reason": text[:200]}
            except Exception as exc:  # noqa: BLE001
                parsed = {"correct": False, "reason": f"judge_error: {type(exc).__name__}"}
            verdicts.append(
                {
                    "id": row["id"],
                    "correct": bool(parsed.get("correct")),
                    "reason": str(parsed.get("reason"))[:300],
                    "expected": row.get("expected_answer"),
                    "answer": (row.get("answer_text") or "")[:400],
                }
            )
            print(f"[{index}/{len(sample)}] {row['id']} -> {parsed.get('correct')}", flush=True)

    correct = sum(1 for verdict in verdicts if verdict["correct"])
    payload = {
        "judge_model": settings.llm_model,
        "independent": False,
        "note": "Same model as the generator; only one model is installed locally.",
        "sample": len(verdicts),
        "correct": correct,
        "rate": round(correct / len(verdicts), 4) if verdicts else None,
        "verdicts": verdicts,
    }
    out = Path(args.run).parent / "judge_report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("judge_model", "sample", "correct", "rate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
