"""OpenAI-compatible chat completion provider.

Works with vLLM, Ollama, TGI, LM Studio, Qwen/DashScope-compatible gateways and
any other server exposing /chat/completions. Nothing in the application imports
the vendor SDK; only httpx is used, so the model can be swapped by configuration.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.observability.logging import get_logger
from app.providers.base import UnavailableProviderError
from app.providers.types import LLMMessage, LLMResponse, ProviderStatus

logger = get_logger(__name__)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used for budget/telemetry only."""
    return max(1, len(text) // 4)


class OpenAICompatibleProvider:
    """Provider for a single OpenAI-compatible endpoint."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 90.0,
        max_tokens: int = 2048,
        temperature: float = 0.1,
        supports_vision: bool = False,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.supports_vision = supports_vision
        self._client: httpx.AsyncClient | None = None
        self._status_cache: tuple[float, ProviderStatus] | None = None

    # -------------------------------------------------------------- plumbing
    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _endpoint(self, path: str) -> str:
        base = self.base_url
        if base.endswith("/chat/completions") or base.endswith("/completions"):
            base = base.rsplit("/", 2)[0]
        return f"{base}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        return self._client

    def _require(self) -> None:
        if not self.configured:
            raise UnavailableProviderError(
                "llm",
                self.name,
                "LLM_BASE_URL / LLM_MODEL are not set",
            )
        if not self.api_key:
            raise UnavailableProviderError(
                "llm",
                self.name,
                "LLM_API_KEY is not set",
            )

    # --------------------------------------------------------------- payload
    def _payload(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
        stream: bool = False,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [m.as_dict() for m in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
            "stream": stream,
        }
        if response_format:
            payload["response_format"] = response_format
        return payload

    # ------------------------------------------------------------ completion
    async def complete(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        self._require()
        started = time.perf_counter()
        payload = self._payload(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        client = self._get_client()
        response = await client.post(self._endpoint("chat/completions"), json=payload, headers=self._headers())
        response.raise_for_status()
        body = response.json()
        choice = (body.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        usage = body.get("usage") or {}
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "llm_completion",
            model=body.get("model", payload["model"]),
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
        )
        return LLMResponse(
            text=text.strip(),
            model=body.get("model", payload["model"]),
            provider=self.name,
            mode="llm",
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        self._require()
        payload = self._payload(
            messages, model=model, temperature=temperature, max_tokens=max_tokens, stream=True
        )
        client = self._get_client()
        async with client.stream(
            "POST", self._endpoint("chat/completions"), json=payload, headers=self._headers()
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    body = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                delta = ((body.get("choices") or [{}])[0].get("delta") or {}).get("content")
                if delta:
                    yield delta

    # ------------------------------------------------------ structured output
    async def complete_structured(
        self,
        messages: Sequence[LLMMessage],
        schema: type[BaseModel],
        *,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BaseModel | None:
        """Return a validated instance of ``schema`` or ``None`` on unusable output."""
        self._require()
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema(), "strict": False},
        }
        try:
            response = await self.complete(
                messages, model=model, temperature=0.0, response_format=response_format
            )
        except httpx.HTTPStatusError:
            # Endpoint rejects response_format: fall back to prompt-guided JSON.
            response = await self.complete(messages, model=model, temperature=0.0)

        parsed = _parse_json(response.text)
        if parsed is not None:
            try:
                return schema.model_validate(parsed)
            except ValidationError:
                logger.warning("structured_output_validation_failed", schema=schema.__name__)
        # Fallback: ask again with an explicit JSON-only instruction.
        retry_messages = list(messages) + [
            LLMMessage(
                role="user",
                content=(
                    "Return ONLY a JSON object matching this JSON Schema, with no prose and no code fences:\n"
                    + json.dumps(schema.model_json_schema())
                ),
            )
        ]
        retry = await self.complete(retry_messages, model=model, temperature=0.0)
        parsed = _parse_json(retry.text)
        if parsed is None:
            return None
        try:
            return schema.model_validate(parsed)
        except ValidationError:
            logger.warning("structured_output_validation_failed_after_retry", schema=schema.__name__)
            return None

    async def complete_structured_payload(
        self,
        messages: Sequence[LLMMessage],
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any] | None:
        """Schema-as-dict variant used when the caller validates events itself."""
        self._require()
        payload = self._payload(messages, model=model, temperature=0.0, max_tokens=None)
        payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
        client = self._get_client()
        response = await client.post(
            self._endpoint("chat/completions"), json=payload, headers=self._headers()
        )
        response.raise_for_status()
        body = response.json()
        text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return _parse_json(text)

    # ----------------------------------------------------------------- status
    async def status(self) -> ProviderStatus:
        if not self.configured:
            return ProviderStatus.of(
                "llm", self.name, False, detail="LLM_BASE_URL and LLM_MODEL are not configured", model=None
            )
        now = time.time()
        if self._status_cache and now - self._status_cache[0] < 30:
            return self._status_cache[1]
        try:
            client = self._get_client()
            response = await client.get(self._endpoint("models"), headers=self._headers(), timeout=5.0)
            reachable = response.status_code < 500
            detail = f"HTTP {response.status_code} from /models"
        except Exception as exc:  # noqa: BLE001 - status must never raise
            reachable = False
            detail = f"unreachable: {type(exc).__name__}"
        status = ProviderStatus.of(
            "llm",
            self.name,
            reachable,
            detail=detail,
            model=self.model,
            supports_vision=self.supports_vision,
        )
        self._status_cache = (now, status)
        return status


def _parse_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    candidate = text.strip()
    match = _JSON_BLOCK.search(candidate)
    if match:
        candidate = match.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None
