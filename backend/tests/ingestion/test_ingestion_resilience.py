"""Ingestion resilience regressions.

Two failures were observed against the real corpus:

* every first-time document stayed at status ``processing`` after a successful
  job, because the job's indexing version (1) was mistaken for a candidate
  version and activation refused to promote a candidate equal to the active one;
* a single unreachable VLM endpoint failed the whole document even though its
  text had already been parsed, OCR'd and chunked.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ingestion.pipeline import IngestionOutcome, IngestionPipeline, is_candidate_version
from app.ingestion.types import ParsedDocument, ParsedPage

# --------------------------------------------------------------- version logic


def test_first_ingestion_is_not_a_candidate_run():
    assert is_candidate_version(candidate_version=1, active_version=1) is False
    assert is_candidate_version(candidate_version=None, active_version=1) is False
    assert is_candidate_version(candidate_version=1, active_version=None) is False


def test_a_newer_version_is_a_candidate_run():
    assert is_candidate_version(candidate_version=2, active_version=1) is True
    assert is_candidate_version(candidate_version=5, active_version=3) is True


# ------------------------------------------------------------- vision outage


class _ExplodingRouter:
    async def vision(self, *args, **kwargs):
        raise RuntimeError("ConnectError: All connection attempts failed")


@pytest.mark.asyncio
async def test_vision_outage_keeps_the_page_and_records_a_warning():
    page = ParsedPage(
        page_number=3,
        text="Lot 1: laboratory consumables",
        image_bytes=b"\x89PNG\r\n\x1a\n",
        needs_vision=True,
    )
    parsed = ParsedDocument(pages=[page], title="notice")
    outcome = IngestionOutcome(document_id="doc_test", status="processing")
    pipeline = SimpleNamespace(
        container=SimpleNamespace(router=_ExplodingRouter()),
        settings=SimpleNamespace(vlm_configured=True),
    )

    await IngestionPipeline._apply_vision(pipeline, parsed, enabled=True, outcome=outcome)

    assert page.text == "Lot 1: laboratory consumables"
    assert page.needs_vision is True
    assert outcome.metrics["vision"] == "unavailable"
    assert outcome.metrics["vision_pages"] == 0
    assert any("Vision escalation failed" in warning for warning in outcome.warnings)


@pytest.mark.asyncio
async def test_vision_disabled_never_calls_the_provider():
    page = ParsedPage(page_number=1, text="text", needs_vision=True)
    parsed = ParsedDocument(pages=[page], title="notice")
    outcome = IngestionOutcome(document_id="doc_test", status="processing")
    pipeline = SimpleNamespace(
        container=SimpleNamespace(router=_ExplodingRouter()),
        settings=SimpleNamespace(vlm_configured=True),
    )

    await IngestionPipeline._apply_vision(pipeline, parsed, enabled=False, outcome=outcome)

    assert outcome.metrics["vision"] == "disabled"
    assert outcome.warnings == []
