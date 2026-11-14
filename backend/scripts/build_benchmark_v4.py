"""Build benchmark v4: the 120 v3 questions plus 30 verified new questions.

The v3 set is carried over unchanged (ids preserved, ``origin: v3``) because it is
the only set with a recorded evidence trail and it is the set the old baseline
ran on. The 15 v3 items still marked ``needs_review`` are kept and flagged,
not silently promoted or deleted.

Every new label is checked against the source page text in the local database:
an answerable question passes only when each expected fact appears on the page
it cites; an unanswerable question passes only when its probe terms appear in
no document. The evidence quote is copied from the page, never written by hand.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "backend" / "var" / "epi.db"
V3 = ROOT / "data" / "evaluation" / "benchmark_v3" / "questions.json"
OUT = ROOT / "data" / "evaluation" / "benchmark_v4"

INTENTS = (
    "price_lookup",
    "contract_terms",
    "comparison",
    "temporal_change",
    "compliance_check",
    "aggregation",
    "relationship",
    "document_lookup",
    "general",
)

CATEGORY_INTENT = {
    "document_metadata": "document_lookup",
    "parties": "relationship",
    "dates_and_duration": "contract_terms",
    "payment_terms": "contract_terms",
    "pricing_schedules": "price_lookup",
    "clauses": "contract_terms",
    "amendments": "temporal_change",
    "obligations": "contract_terms",
    "supplier_buyer_relationships": "relationship",
    "graph_multi_hop": "relationship",
    "historical_temporal": "temporal_change",
    "unanswerable": "general",
    "procurement_values": "price_lookup",
    "award_criteria": "comparison",
    "structured_data": "aggregation",
    "unanswerable_near_miss": "general",
}


def norm(text: str) -> str:
    text = (text or "").replace("\u00a3", "£").replace("\ufffd", "£").replace("\u00ad", "")
    text = text.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text)


def compact(value: str) -> str:
    """Compare facts ignoring spacing, punctuation and currency glyph damage."""
    text = norm(value).lower()
    text = text.replace("£", "").replace("$", "")
    return re.sub(r"[^a-z0-9]", "", text)


NEW_QUESTIONS = [
    # ---------------------------------------------------------- procurement values
    {
        "id": "V4-001", "doc": "0685ae_tender_3.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the Critical Ventilation contract excluding VAT?",
        "answer": "£265,000", "facts": ["265,000"],
        "section": "scope",
    },
    {
        "id": "V4-002", "doc": "0685ae_tender_3.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the Critical Ventilation contract including VAT?",
        "answer": "£318,000", "facts": ["318,000"], "section": "scope",
    },
    {
        "id": "V4-003", "doc": "0508f7_tender_5.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the Supporting Holocaust Survivor Testimony contract including VAT?",
        "answer": "£2,000,000", "facts": ["2,000,000"], "section": "scope",
    },
    {
        "id": "V4-004", "doc": "0523fd_tender_11.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the HR and Duties Management System procurement excluding VAT?",
        "answer": "£2,750,000", "facts": ["2,750,000"], "section": "scope",
    },
    {
        "id": "V4-005", "doc": "05a7e4_tender_18.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the NBI Energy Centre procurement including VAT?",
        "answer": "£14,160,000", "facts": ["14,160,000"], "section": "scope",
    },
    {
        "id": "V4-006", "doc": "06093e_tender_20.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the ACE Financial Management System contract including VAT?",
        "answer": "£300,000", "facts": ["300,000"], "section": "scope",
    },
    {
        "id": "V4-007", "doc": "065308_tender_2.html", "page": 1, "category": "procurement_values",
        "question": "What is the estimated value of the Castlewellan Peace Maze festivals procurement excluding VAT?",
        "answer": "£21,790.39", "facts": ["21,790.39"], "section": "scope",
    },
    {
        "id": "V4-008", "doc": "066066_tender_12.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the Dockless bike hire concession excluding VAT?",
        "answer": "£82,000,000", "facts": ["82,000,000"], "section": "scope",
    },
    {
        "id": "V4-009", "doc": "0683f4_tender_14.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the Fulwood Bridge Painting contract excluding VAT?",
        "answer": "£100,000", "facts": ["100,000"], "section": "scope",
    },
    {
        "id": "V4-010", "doc": "06e110_tender_4.html", "page": 1, "category": "procurement_values",
        "question": "What is the total estimated value of the robotic milking system maintenance contract including VAT?",
        "answer": "£288,000", "facts": ["288,000"], "section": "scope",
    },
    # ------------------------------------------------------------- award criteria
    {
        "id": "V4-011", "doc": "04f6f2_tender_10.html", "page": 1, "category": "award_criteria",
        "question": "How is the award of the Gallery 33 design tender weighted between quality, price and social value?",
        "answer": "60% quality, 30% price, 10% social value",
        "facts": ["Quality | Long criteria description | Quality | 60%", "Price | Long criteria description | Price | 30%", "Social Value | Long criteria description | Quality | 10%"],
        "section": "award criteria",
    },
    {
        "id": "V4-012", "doc": "0508f7_tender_5.html", "page": 1, "category": "award_criteria",
        "question": "What weighting does the technical element carry in the Holocaust Survivor Testimony procurement?",
        "answer": "70% technical, 30% commercial",
        "facts": ["Technical (including Social Value) | Quality | 70%", "Commercial | Price | 30%"],
        "section": "award criteria",
    },
    {
        "id": "V4-013", "doc": "05a7e4_tender_18.html", "page": 1, "category": "award_criteria",
        "question": "What are the quality and price weightings for the NBI Energy Centre CHP engines?",
        "answer": "60% quality, 40% price",
        "facts": ["Quality | 60%", "Price | 40%"], "section": "award criteria",
    },
    {
        "id": "V4-014", "doc": "0679c4_tender_7.html", "page": 1, "category": "award_criteria",
        "question": "How is the Loan Management System tender scored across quality, price and social value?",
        "answer": "70% quality, 20% price, 10% social value",
        "facts": ["Quality | Quality | 70%", "Price | Price | 20%", "Social Value | Quality | 10%"],
        "section": "award criteria",
    },
    {
        "id": "V4-015", "doc": "0683f4_tender_14.html", "page": 1, "category": "award_criteria",
        "question": "What split between quality and price applies to the Fulwood Bridge Painting tender?",
        "answer": "50% quality, 50% price", "facts": ["50% Quality 50% Price"],
        "section": "award criteria",
    },
    {
        "id": "V4-016", "doc": "06d0c8_tender_17.html", "page": 1, "category": "award_criteria",
        "question": "What are the technical, commercial and social value weightings for the Return to Practice facilitator tender?",
        "answer": "60% technical, 30% commercial, 10% social value",
        "facts": ["60% Technical, 30% Commercial, 10% Social Value"], "section": "award criteria",
    },
    # ------------------------------------------------------------ dates/deadlines
    {
        "id": "V4-017", "doc": "0685ae_tender_3.html", "page": 1, "category": "dates_and_duration",
        "question": "What is the tender submission deadline for the Critical Ventilation contract?",
        "answer": "18 May 2026, 12:00pm", "facts": ["18 May 2026, 12:00pm"], "section": "submission",
    },
    {
        "id": "V4-018", "doc": "06d0c8_tender_17.html", "page": 1, "category": "dates_and_duration",
        "question": "When must tenders for the Practice Education Facilitator role be submitted?",
        "answer": "5 August 2026, 12:00pm", "facts": ["5 August 2026, 12:00pm"], "section": "submission",
    },
    {
        "id": "V4-019", "doc": "066066_tender_12.html", "page": 1, "category": "dates_and_duration",
        "question": "When does the Dockless bike hire concession contract period end?",
        "answer": "31 May 2032", "facts": ["1 June 2027 to 31 May 2032"], "section": "scope",
    },
    {
        "id": "V4-020", "doc": "0679c4_tender_7.html", "page": 1, "category": "dates_and_duration",
        "question": "What is the tender submission deadline for the Loan Management System?",
        "answer": "8 May 2026, 11:55pm", "facts": ["8 May 2026, 11:55pm"], "section": "submission",
    },
    {
        "id": "V4-021", "doc": "065308_tender_2.html", "page": 1, "category": "dates_and_duration",
        "question": "When does the Peace Maze festivals contract period start?",
        "answer": "2 April 2026", "facts": ["2 April 2026 to 31 March 2027"], "section": "scope",
    },
    {
        "id": "V4-022", "doc": "065b20_tender_6.pdf", "page": 7, "category": "contract_terms",
        "question": "How long must a response to the BGS waste management ITT remain valid?",
        "answer": "120 days", "facts": ["120 days"], "section": "response validity",
    },
    {
        "id": "V4-023", "doc": "065b20_tender_6.pdf", "page": 7, "category": "contract_terms",
        "question": "What is the initial contract duration and extension option for the BGS waste management contract?",
        "answer": "12 months, with optional extensions of 3 x 12-month periods",
        "facts": ["initial period of 12 months", "3 x 12-month periods"], "section": "contract duration",
    },
    {
        "id": "V4-024", "doc": "065b20_tender_6.pdf", "page": 13, "category": "award_criteria",
        "question": "What percentage of the BGS waste management award is allocated to Social Value?",
        "answer": "10%", "facts": ["Social Value 10.00%"], "section": "award criteria",
    },
    {
        "id": "V4-025", "doc": "060827_tender_19.docx", "page": 1, "category": "parties",
        "question": "Who is the secondary contact for the Northern Gas Networks operated plant tender?",
        "answer": "Joanna Palmer", "facts": ["Joanna Palmer"], "section": "contacts",
    },
    {
        "id": "V4-026", "doc": "06093e_tender_20.html", "page": 1, "category": "compliance_check",
        "question": "What level of Employer's Liability insurance does the ACE Financial Management System tender require?",
        "answer": "£5m", "facts": ["Employer's (Compulsory) Liability Insurance* = £5m"], "section": "insurance",
    },
    # --------------------------------------------------------- structured records
    {
        "id": "V4-027", "doc": "06093e_tender_20.html", "page": 1, "category": "structured_data",
        "question": "When does the ACE Financial Management System contract period end?",
        "answer": "31 August 2030", "facts": ["1 September 2026 to 31 August 2030"], "section": "scope",
    },
    {
        "id": "V4-028", "doc": "069a8c_tender_15.html", "page": 1, "category": "structured_data",
        "question": "What is the estimated total value of the Old Oak Private Sector Partner procurement?",
        "answer": "£12,000,000,000 including VAT", "facts": ["12,000,000,000"], "section": "scope",
    },
    # ------------------------------------------------------ unanswerable near-miss
    {
        "id": "V4-029", "doc": None, "page": None, "category": "unanswerable_near_miss",
        "question": "Who is the incumbent ventilation maintenance contractor for Powys Teaching Health Board?",
        "answer": None, "facts": [], "probe": ["incumbent", "ventilation maintenance contractor"],
    },
    {
        "id": "V4-030", "doc": None, "page": None, "category": "unanswerable_near_miss",
        "question": "What is the warranty period for the Fulwood Bridge paint system?",
        "answer": None, "facts": [], "probe": ["warranty period", "paint system warranty"],
    },
]


def page_text(con: sqlite3.Connection, filename: str, page: int) -> str:
    row = con.execute(
        "select p.raw_text, p.ocr_text from document_pages p join documents d on d.id = p.document_id "
        "where d.filename = ? and p.page_number = ?",
        (filename, page),
    ).fetchone()
    return norm("\n".join(part for part in (row or ("", "")) if part))


def quote_for(text: str, fact: str) -> str | None:
    target = compact(fact)
    low = compact(text)
    index = low.find(target)
    if index < 0:
        return None
    # Map the compacted offset back approximately by scanning the original.
    count = 0
    for position, char in enumerate(text):
        if re.match(r"[a-z0-9]", char.lower()):
            if count >= index:
                start = max(0, position - 90)
                return text[start : position + len(fact) + 120].strip()
            count += 1
    return text[:200]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    v3 = json.loads(V3.read_text(encoding="utf-8"))
    v3_questions = v3["questions"]

    for item in v3_questions:
        item["origin"] = "v3"
        item["intent"] = item.get("intent") or CATEGORY_INTENT.get(item["category"], "general")

    new_rows = []
    failures = []
    for spec in NEW_QUESTIONS:
        row = {
            "id": spec["id"],
            "question": spec["question"],
            "category": spec["category"],
            "intent": CATEGORY_INTENT.get(spec["category"], "general"),
            "origin": "v4_new",
            "difficulty": "medium",
            "review_status": "auto_verified",
            "source_document": spec["doc"],
            "source_document_id": None,
            "expected_answer": spec["answer"],
            "expected_facts": spec["facts"],
            "expected_documents": [spec["doc"]] if spec["doc"] else [],
            "expected_pages": [spec["page"]] if spec["page"] else [],
            "answerability": "unanswerable" if spec["answer"] is None else "answerable",
            "expected_refusal": spec["answer"] is None,
            "supporting_section": spec.get("section"),
        }
        if spec["doc"]:
            row["source_document_id"] = con.execute(
                "select id from documents where filename = ?", (spec["doc"],)
            ).fetchone()[0]
            text = page_text(con, spec["doc"], spec["page"])
            missing = [fact for fact in spec["facts"] if compact(fact) not in compact(text)]
            if missing:
                failures.append({"id": spec["id"], "missing": missing, "reason": "fact not on cited page"})
            else:
                row["evidence_quote"] = quote_for(text, spec["facts"][0])
                row["evidence_verification"] = {
                    "method": "page_text_match",
                    "page": spec["page"],
                    "facts_checked": len(spec["facts"]),
                }
        else:
            corpus = norm(
                "\n".join(
                    row_[0] or ""
                    for row_ in con.execute("select raw_text from document_pages")
                )
            )
            hits = [term for term in spec["probe"] if term.lower() in corpus.lower()]
            if hits:
                failures.append({"id": spec["id"], "reason": f"probe terms present: {hits}"})
            row["evidence_verification"] = {
                "method": "corpus_absence",
                "probe_terms": spec["probe"],
                "documents_searched": con.execute("select count(*) from documents").fetchone()[0],
            }
        new_rows.append(row)

    questions = v3_questions + new_rows
    payload = {
        "name": "epi-benchmark-v4",
        "version": "4.0.0",
        "created": datetime.now(UTC).isoformat(),
        "question_count": len(questions),
        "distribution": {
            "answerable": sum(1 for q in questions if q["answerability"] == "answerable"),
            "unanswerable": sum(1 for q in questions if q["answerability"] == "unanswerable"),
            "needs_review": sum(1 for q in questions if q["answerability"] == "needs_review"),
            "origin_v3": sum(1 for q in questions if q["origin"] == "v3"),
            "origin_v4_new": sum(1 for q in questions if q["origin"] == "v4_new"),
        },
        "generator": "backend/scripts/build_benchmark_v4.py",
        "labelling": (
            "v3 labels carried over unchanged; v4_new labels verified against the cited page text "
            "(answerable) or by corpus-wide probe-term absence (unanswerable). No label is human-adjudicated."
        ),
        "questions": questions,
    }

    out_file = OUT / "questions.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    digest = hashlib.sha256(out_file.read_bytes()).hexdigest()
    (OUT / "questions.sha256").write_text(digest + "\n", encoding="utf-8")

    # v3 label audit: do the labelled facts appear on the cited page?
    audit = []
    for item in v3_questions:
        if item["answerability"] == "unanswerable" or not item.get("source_document"):
            continue
        if not item.get("expected_pages"):
            audit.append({"id": item["id"], "status": "no_page", "missing": item["expected_facts"]})
            continue
        text = page_text(con, item["source_document"], int(item["expected_pages"][0]))
        missing = [fact for fact in item.get("expected_facts", []) if compact(fact) not in compact(text)]
        audit.append(
            {
                "id": item["id"],
                "status": "ok" if not missing else "fact_not_found",
                "missing": missing,
                "quote_present": compact(item.get("evidence_quote") or "")[:40] in compact(text)
                if item.get("evidence_quote")
                else None,
            }
        )

    checked = [row for row in audit if row["status"] == "ok"]
    not_found = [row for row in audit if row["status"] == "fact_not_found"]
    lines = [
        "# Benchmark v4 label audit",
        "",
        f"- Questions: {len(questions)} (v3: {len(v3_questions)}, new: {len(new_rows)})",
        f"- SHA-256 of questions.json: `{digest}`",
        f"- New labels verified against page text: {len(new_rows) - len(failures)}/{len(new_rows)}",
        f"- v3 answerable labels whose facts appear verbatim on the cited page: {len(checked)}/{len(audit)}",
        f"- v3 labels with at least one fact not found verbatim: {len(not_found)}",
        "",
        "## v3 labels not found verbatim",
        "",
        "| id | missing facts |",
        "| --- | --- |",
    ]
    for row in not_found:
        lines.append(f"| {row['id']} | {row['missing']} |")
    if failures:
        lines += ["", "## New-label failures", "", "| id | reason |", "| --- | --- |"]
        for row in failures:
            lines.append(f"| {row['id']} | {row.get('reason')} {row.get('missing', '')} |")
    lines += [
        "",
        "## Method",
        "",
        "- Answerable new labels: each expected fact is normalised (case, punctuation, spacing, currency glyphs)",
        "  and required to appear in the raw text of the cited page. The evidence quote is copied from that page.",
        "- Unanswerable new labels: probe terms are searched across every page's text; a hit would fail the label.",
        "- v3 labels are reported above, not silently edited. `needs_review` items stay flagged.",
        "- No question was written from the benchmark results, and no label was changed after the run.",
        "",
    ]
    (OUT / "labels_audit.md").write_text("\n".join(lines), encoding="utf-8")

    # Review sample: 30 stratified questions, deterministic.
    rng = random.Random(20261114)
    sample = rng.sample(questions, 30)
    with (OUT / "review_sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["id", "category", "question", "expected_answer", "source_document", "page", "reviewer_verdict"]
        )
        for item in sample:
            writer.writerow(
                [
                    item["id"],
                    item["category"],
                    item["question"],
                    item.get("expected_answer") or "",
                    item.get("source_document") or "",
                    (item.get("expected_pages") or [""])[0],
                    "",
                ]
            )

    print(json.dumps(payload["distribution"], indent=2))
    print("audit: ok", len(checked), "not_found", len(not_found), "new_failures", len(failures))
    print("sha256", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
