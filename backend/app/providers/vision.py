"""Vision provider (Qwen3-VL family by default).

Used *selectively*: only pages that the layout/text analysis flags as visually
complex (scanned, table-heavy, stamp/signature-bearing) are escalated, because
sending every page to a VLM would wreck both latency and cost (PRD s.13/s.38).
"""

from __future__ import annotations

import base64
import time

import httpx

from app.observability.logging import get_logger
from app.providers.types import ProviderStatus, VisionResponse

logger = get_logger(__name__)


class OpenAICompatibleVisionProvider:
    name = "openai_compatible_vlm"

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 120.0,
        max_tokens: int = 1024,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self._client: httpx.AsyncClient | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def _endpoint(self) -> str:
        base = self.base_url
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    async def describe(
        self,
        image_bytes: bytes,
        prompt: str,
        *,
        mime_type: str = "image/png",
        model: str | None = None,
    ) -> VisionResponse:
        if not self.configured:
            return VisionResponse(
                text="",
                provider=self.name,
                model=None,
                mode="unavailable",
            )
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds)
        payload = {
            "model": model or self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
                            },
                        },
                    ],
                }
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        started = time.perf_counter()
        response = await self._client.post(self._endpoint(), json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
        text = ((body.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info("vlm_completed", model=payload["model"], latency_ms=latency_ms)
        return VisionResponse(
            text=text.strip(), provider=self.name, model=payload["model"], mode="vlm", latency_ms=latency_ms
        )

    async def status(self) -> ProviderStatus:
        if not self.configured:
            return ProviderStatus.of(
                "vision",
                self.name,
                False,
                detail="VLM endpoint not configured (VLM_BASE_URL / VLM_API_KEY)",
                model=None,
            )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    self._endpoint().rsplit("/", 2)[0] + "/models",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                )
            return ProviderStatus.of(
                "vision",
                self.name,
                response.status_code < 500,
                detail=f"HTTP {response.status_code} from /models",
                model=self.model,
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderStatus.of(
                "vision", self.name, False, detail=f"unreachable: {type(exc).__name__}", model=self.model
            )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
