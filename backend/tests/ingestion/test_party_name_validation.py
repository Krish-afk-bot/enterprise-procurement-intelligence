"""Party extraction must not turn prose into supplier entities.

Real notices say "between the Council and any other party". The extraction
patterns matched those phrases, the pipeline created supplier records named
"the council" and "the rest of the country", and the graph carried them as
entities. A supplier name has to look like a name; corpus labels such as
"Supplier A" stay valid because the letter identifies the party.
"""

from __future__ import annotations

import pytest

from app.ingestion.metadata import _clean_party, extract_metadata
from app.ingestion.types import ParsedDocument, ParsedPage


def document(text: str) -> ParsedDocument:
    return ParsedDocument(pages=[ParsedPage(page_number=1, text=text)], plain_text=text)


class TestGenericProseIsRejected:
    @pytest.mark.parametrize(
        "phrase",
        [
            "the council",
            "any other party",
            "the rest of the country",
            "each supplier",
            "such authority",
        ],
    )
    def test_generic_phrases_are_not_names(self, phrase: str) -> None:
        assert _clean_party(phrase) == ""

    def test_parties_sentence_does_not_create_a_supplier(self) -> None:
        metadata = extract_metadata(
            document("This agreement is between the Council and any other party."),
            filename="notice.html",
        )
        assert metadata.supplier_name is None

    def test_generic_field_value_does_not_create_a_supplier(self) -> None:
        metadata = extract_metadata(
            document("Supplier name: the rest of the country\n"),
            filename="notice.html",
        )
        assert metadata.supplier_name is None


class TestRealNamesSurvive:
    def test_company_name_is_kept(self) -> None:
        metadata = extract_metadata(
            document(
                "This agreement is between the Financial Services Compensation Scheme and "
                "C. & P. ENGINEERING SERVICES LIMITED.\n"
            ),
            filename="064670_tender_1.html",
        )
        assert metadata.supplier_name == "C. & P. ENGINEERING SERVICES LIMITED"

    def test_corpus_label_is_kept(self) -> None:
        metadata = extract_metadata(
            document("Supplier name: Supplier A\n"),
            filename="supplier_a_master_contract.pdf",
        )
        assert metadata.supplier_name == "Supplier A"

    def test_leading_article_is_kept_when_the_name_is_a_name(self) -> None:
        assert _clean_party("The Stationery Office Ltd") == "The Stationery Office Ltd"
