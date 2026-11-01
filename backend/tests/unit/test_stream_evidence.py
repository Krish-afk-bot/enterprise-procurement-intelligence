"""The stream emits evidence before the answer, and answers carry their conversation."""

from __future__ import annotations

from app.agents.pipeline import _evidence_preview
from app.schemas.query import AnswerOut


def test_evidence_preview_shapes_hits_as_citations() -> None:
    state = {
        "retrieval": {
            "hits": [
                {
                    "chunk_id": "chk_1",
                    "document_id": "doc_1",
                    "document_name": "supplier_a_amendment_2.pdf",
                    "document_type": "amendment",
                    "page": 1,
                    "section": "Price Revision",
                    "clause": None,
                    "content": "The unit price for Industrial Laptop X200 is revised to USD 874.00.",
                    "rerank_score": 0.91,
                    "fused_score": 0.02,
                    "rank": 1,
                    "is_synthetic": True,
                }
            ]
        }
    }
    preview = _evidence_preview(state)
    assert len(preview) == 1
    assert preview[0]["document_name"] == "supplier_a_amendment_2.pdf"
    assert preview[0]["page"] == 1
    assert preview[0]["label"] == "supplier_a_amendment_2.pdf — p.1"
    assert preview[0]["score"] == 0.91
    assert "874.00" in preview[0]["snippet"]
    assert preview[0]["verified"] is True


def test_evidence_preview_is_empty_before_retrieval() -> None:
    assert _evidence_preview({}) == []


def test_answer_can_carry_the_conversation_created_lazily() -> None:
    answer = AnswerOut(query_id="qry_1", conversation_id="cnv_1", answer_text="ok")
    assert answer.conversation_id == "cnv_1"
    assert AnswerOut(query_id="qry_2", answer_text="ok").conversation_id is None
