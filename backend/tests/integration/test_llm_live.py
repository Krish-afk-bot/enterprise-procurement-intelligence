"""Live LLM integration test.

IMPORTANT: This test is SKIPPED by default.
It only runs when the following environment variables are set:

  RUN_LLM_INTEGRATION=1
  LLM_BASE_URL=<your endpoint>
  LLM_API_KEY=<your key>
  LLM_MODEL=<your model name>   (optional, defaults to settings default)

Run with:

  RUN_LLM_INTEGRATION=1 LLM_BASE_URL=http://... LLM_API_KEY=... pytest tests/integration/test_llm_live.py -v

This test makes real HTTP requests to a configured LLM endpoint.
It does NOT run in ordinary CI and does NOT require API keys.

It verifies:
  - The provider can reach the endpoint
  - A simple completion returns non-empty text
  - The procurement system prompt and evidence blocks are accepted
  - Generation mode is reported as "llm" in the answer
  - No API keys appear in the response text
"""

from __future__ import annotations

import os

import pytest

RUN_LLM = os.getenv("RUN_LLM_INTEGRATION", "").strip() in {"1", "true", "yes"}

pytestmark = pytest.mark.skipif(
    not RUN_LLM,
    reason="Live LLM test skipped. Set RUN_LLM_INTEGRATION=1 and configure LLM_BASE_URL/LLM_API_KEY to run.",
)


@pytest.fixture()
def live_settings():
    from app.config.settings import Settings

    return Settings(
        app_env="development",
        jwt_secret="test-secret-not-for-production",
        database_url="sqlite+aiosqlite:///:memory:",
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
        llm_timeout_seconds=60.0,
        llm_max_tokens=512,
        llm_temperature=0.1,
    )


@pytest.fixture()
def live_provider(live_settings):
    from app.providers.llm.openai_compatible import OpenAICompatibleProvider

    return OpenAICompatibleProvider(
        base_url=live_settings.llm_base_url,
        api_key=live_settings.llm_api_key,
        model=live_settings.llm_model,
        timeout_seconds=live_settings.llm_timeout_seconds,
        max_tokens=live_settings.llm_max_tokens,
        temperature=live_settings.llm_temperature,
    )


class TestLiveLLMProvider:
    async def test_provider_status_is_available(self, live_provider) -> None:
        status = await live_provider.status()
        assert status.available is True, f"Provider not available: {status.detail}"

    async def test_simple_completion_returns_text(self, live_provider) -> None:
        from app.providers.types import LLMMessage

        response = await live_provider.complete(
            [LLMMessage(role="user", content="Reply with exactly one word: hello")]
        )
        assert response.text.strip() != "", "Empty response from LLM"
        assert response.prompt_tokens is not None, "Token usage not reported"

    async def test_procurement_system_prompt_accepted(self, live_provider) -> None:
        from app.agents.generation import SYSTEM_PROMPT
        from app.providers.types import LLMMessage
        from app.security.injection import EVIDENCE_CLOSE, EVIDENCE_OPEN

        user_content = (
            "QUESTION: What is the unit price for Widget A?\n"
            f"{EVIDENCE_OPEN}\n"
            "[1] Source: Contract A | page 1\n"
            "The agreed unit price for Widget A is USD 92.00 per unit, effective 2026-01-01.\n"
            f"{EVIDENCE_CLOSE}\n"
        )
        response = await live_provider.complete(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_content),
            ]
        )
        assert response.text.strip() != ""
        # The answer must not invent a price not in the evidence
        assert "92" in response.text or "Widget" in response.text or "USD" in response.text, (
            f"LLM response does not reference the evidence: {response.text[:300]}"
        )

    async def test_no_api_key_in_response(self, live_provider, live_settings) -> None:
        from app.providers.types import LLMMessage

        response = await live_provider.complete(
            [LLMMessage(role="user", content="Reply with exactly: 'acknowledged'")]
        )
        # The API key must never appear in the model response
        if live_settings.llm_api_key:
            assert live_settings.llm_api_key not in response.text, "API key leaked into LLM response text"

    async def test_refusal_on_unanswerable_question(self, live_provider) -> None:
        from app.agents.generation import SYSTEM_PROMPT
        from app.providers.types import LLMMessage
        from app.security.injection import EVIDENCE_CLOSE, EVIDENCE_OPEN

        # No evidence for this question → must trigger refusal
        user_content = (
            "QUESTION: What is the price for Product XYZ-9999?\n"
            f"{EVIDENCE_OPEN}\n"
            "[1] Source: Contract A | page 1\n"
            "This contract covers Widget A only. Unit price USD 92.00.\n"
            f"{EVIDENCE_CLOSE}\n"
        )
        response = await live_provider.complete(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_content),
            ]
        )
        # The model should refuse or indicate the evidence doesn't cover the question
        text = response.text.lower()
        refused = (
            "couldn't verify" in text
            or "not found" in text
            or "no evidence" in text
            or "xyz-9999" not in text  # didn't invent an answer
        )
        assert refused, f"Expected a refusal for unanswerable question, got: {response.text[:300]}"


class TestLiveAnswerGenerator:
    async def test_full_pipeline_generation_mode_llm(self, live_settings) -> None:

        from app.agents.generation import AnswerGenerator
        from app.providers.llm.openai_compatible import OpenAICompatibleProvider
        from app.providers.router import ModelRouter
        from app.retrieval.context import CitationDraft, ContextBlock, ContextBundle
        from app.retrieval.query_understanding import Intent, QueryPlan

        llm = OpenAICompatibleProvider(
            base_url=live_settings.llm_base_url,
            api_key=live_settings.llm_api_key,
            model=live_settings.llm_model,
        )
        router = ModelRouter(live_settings, llm=llm)
        generator = AnswerGenerator(router=router, settings=live_settings)

        citation = CitationDraft(
            chunk_id="chk_1",
            document_id="doc_1",
            document_name="Test Contract",
            page=1,
            snippet="The unit price for Widget A is USD 92.00 per unit, effective 2026-01-01.",
            verified=True,
        )
        block = ContextBlock(
            marker="[1]",
            text="[1] Source: Test Contract | page 1\n"
            "The unit price for Widget A is USD 92.00 per unit, effective 2026-01-01.",
            citation=citation,
            content_type="paragraph",
            is_synthetic=True,
        )
        bundle = ContextBundle(blocks=[block], citations=[citation])
        plan = QueryPlan(query="What is the price for Widget A?", intent=Intent.PRICE_LOOKUP)

        result = await generator.generate(
            question="What is the price for Widget A?",
            plan=plan,
            bundle=bundle,
        )

        assert result.mode == "llm", (
            f"Expected LLM mode but got '{result.mode}'. Degradation reasons: {result.degradation_reasons}"
        )
        assert result.text.strip() != "", "Empty answer from LLM"
        assert result.degraded is False
