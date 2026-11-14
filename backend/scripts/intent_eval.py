"""Intent-classification check on 45 fresh, hand-labelled queries.

The queries are written for this report (not sampled from the benchmark) so the
accuracy is not measured on the same text the labels were derived from. The
classifier is the production rule-based understander; nothing is tuned here.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.retrieval.query_understanding import understand_query_rule_based  # noqa: E402

LABELLED = {
    "price_lookup": [
        "What is the estimated value of the Critical Ventilation contract?",
        "How much is the ACE financial management system worth?",
        "What price did the council budget for the Peace Maze festivals?",
        "What is the total contract value including VAT for the bike hire concession?",
        "What does the BGS waste management contract cost per year?",
    ],
    "contract_terms": [
        "What payment terms apply to the robotic milking system contract?",
        "How long does the BGS waste management contract run initially?",
        "What is the response validity period for the UKRI tender?",
        "Which clause covers termination of the loan management contract?",
        "What insurance cover must the supplier hold for the ACE contract?",
    ],
    "comparison": [
        "Which tender has the higher estimated value, Gallery 33 or Critical Ventilation?",
        "Compare the payment terms of the ACE and Aberystwyth contracts.",
        "Is the Holocaust testimony contract longer than the Peace Maze contract?",
        "Which procurement offers the higher quality weighting, NBI Energy Centre or Old Oak?",
        "How does the Camden bike hire value compare with the Fulwood bridge painting value?",
    ],
    "temporal_change": [
        "What did the second amendment to the Old Oak procurement change?",
        "As of 1 January 2026, what was the recorded value of contract NS-2024-001?",
        "Which contract superseded ORC-2021-777?",
        "How has the closing date for the loan management system changed?",
        "What was the publication date before the latest revision of the BGS notice?",
    ],
    "compliance_check": [
        "Does the supplier hold ISO 27001 certification?",
        "Which GDPR certificates are linked to the ACE supplier?",
        "Is Northwind compliant with the Modern Slavery Act?",
        "What employer's liability insurance level is required?",
        "Are there any audit non-conformities recorded for the supplier?",
    ],
    "aggregation": [
        "How many documents are in the workspace?",
        "How many contracts does Helios Technology Partners hold?",
        "What is the total value of all active contracts?",
        "How many ingestion jobs failed?",
        "How many suppliers are recorded in total?",
    ],
    "relationship": [
        "Which supplier is linked to contract HTP-2024-014?",
        "Who is the buyer for the NBI Energy Centre?",
        "Which contracts does Orion Components Co hold?",
        "What is the relationship between the British Business Bank and the loan system supplier?",
        "Who is the named contact for the Northern Gas Networks tender?",
    ],
    "document_lookup": [
        "What is the notice identifier for the Fulwood Bridge Painting tender?",
        "Show me the document 0685ae_tender_3.html.",
        "What OCID identifies the Gallery 33 procurement?",
        "What type of notice is 06d2dd_tender_8?",
        "Find the tender titled Provision of Operated Plant.",
    ],
    "general": [
        "Summarise the procurement landscape in these documents.",
        "What should I know before bidding for council work?",
        "Explain the difference between a framework and a dynamic market.",
        "What are common risks in facilities management contracts?",
        "Give me an overview of the waste management requirement.",
    ],
}


def main() -> int:
    rows = []
    for expected, queries in LABELLED.items():
        for question in queries:
            plan = understand_query_rule_based(question)
            rows.append({"query": question, "expected": expected, "predicted": str(plan.intent)})

    correct = sum(1 for row in rows if row["expected"] == row["predicted"])
    confusion: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        confusion[row["expected"]][row["predicted"]] += 1
    per_intent = {}
    for intent in LABELLED:
        total = sum(1 for row in rows if row["expected"] == intent)
        hit = sum(1 for row in rows if row["expected"] == intent and row["predicted"] == intent)
        per_intent[intent] = {"correct": hit, "total": total, "accuracy": round(hit / total, 3)}

    payload = {
        "sample_size": len(rows),
        "accuracy": round(correct / len(rows), 4),
        "per_intent": per_intent,
        "confusion": {key: dict(value) for key, value in confusion.items()},
        "rows": rows,
    }
    out = ROOT.parent / "data" / "evaluation" / "benchmark_v4"
    (out / "intent_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"accuracy": payload["accuracy"], "per_intent": per_intent}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
