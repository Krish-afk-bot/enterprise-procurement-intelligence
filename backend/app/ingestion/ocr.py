"""OCR.

Triggered only when a page has little or no extractable text (PRD s.23). The
engine is loaded lazily and its availability is *reported*: if PaddleOCR cannot
initialise (missing models, no network for a first-time download, incompatible
runtime) the pipeline records ``ocr: unavailable`` on the document rather than
pretending the page was read.
"""

from __future__ import annotations

import asyncio
import io
import os
from dataclasses import dataclass

from app.observability.logging import get_logger

logger = get_logger(__name__)

#: PaddleOCR performs a connectivity check on first use; the platform controls
#: when models are fetched, so the check is disabled.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

#: The oneDNN (MKL-DNN) kernels shipped with some Paddle CPU builds fail with
#: "ConvertPirAttribute2RuntimeAttribute not support" on the PIR execution path.
#: Disabling oneDNN selects a supported kernel set. Both the env flag and the
#: constructor argument are set because Paddle reads the flag at import time.
os.environ.setdefault("FLAGS_use_mkldnn", "0")


@dataclass(slots=True)
class OcrResult:
    text: str
    engine: str
    available: bool
    detail: str = ""
    line_count: int = 0


class OcrEngine:
    """Lazy PaddleOCR wrapper."""

    name = "paddleocr"

    def __init__(self, *, enabled: bool = True, language: str = "en", use_onednn: bool = False) -> None:
        self.enabled = enabled
        self.language = language
        self.use_onednn = use_onednn
        self._engine = None
        self._lock = asyncio.Lock()
        self._error: str | None = None
        self._attempted = False

    @property
    def available(self) -> bool:
        return self.enabled and self._engine is not None

    def _load(self) -> None:
        from paddleocr import PaddleOCR

        kwargs: dict[str, object] = {"lang": self.language, "use_textline_orientation": True}
        if not self.use_onednn:
            kwargs["enable_mkldnn"] = False
        try:
            self._engine = PaddleOCR(**kwargs)
        except TypeError:
            # Older/newer signature differences: retry with the minimal set.
            kwargs.pop("enable_mkldnn", None)
            try:
                self._engine = PaddleOCR(**kwargs)
            except TypeError:
                self._engine = PaddleOCR(use_angle_cls=True, lang=self.language)

    async def ensure_loaded(self) -> bool:
        if not self.enabled:
            self._error = "disabled by configuration"
            return False
        if self._engine is not None:
            return True
        if self._attempted and self._error:
            return False
        async with self._lock:
            if self._engine is not None:
                return True
            self._attempted = True
            try:
                await asyncio.to_thread(self._load)
                logger.info("ocr_engine_loaded", engine=self.name, lang=self.language)
                self._error = None
            except Exception as exc:  # noqa: BLE001
                self._error = f"{type(exc).__name__}: {exc}"
                logger.warning("ocr_engine_unavailable", error=self._error)
        return self._engine is not None

    async def ocr_image(self, image_bytes: bytes) -> OcrResult:
        if not await self.ensure_loaded():
            return OcrResult(text="", engine=self.name, available=False, detail=self._error or "unavailable")

        def _run() -> tuple[str, int]:
            import numpy as np
            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as image:
                array = np.asarray(image.convert("RGB"))
            lines: list[str] = []
            engine = self._engine
            predict = getattr(engine, "predict", None)
            if callable(predict):
                for result in predict(array) or []:
                    lines.extend(_texts_from_result(result))
            else:
                result = engine.ocr(array, cls=True) or []
                for page in result:
                    for entry in page or []:
                        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                            value = entry[1]
                            if isinstance(value, (list, tuple)) and value:
                                lines.append(str(value[0]))
            return "\n".join(line for line in lines if line), len(lines)

        try:
            text, count = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001
            self._error = f"{type(exc).__name__}: {exc}"
            logger.warning("ocr_failed", error=self._error)
            return OcrResult(text="", engine=self.name, available=False, detail=self._error)

        return OcrResult(text=text, engine=self.name, available=True, line_count=count)

    async def status(self) -> dict[str, object]:
        return {
            "engine": self.name,
            "enabled": self.enabled,
            "available": self.available,
            "detail": self._error or ("loaded" if self.available else "not loaded yet"),
            "language": self.language,
        }


def _texts_from_result(result: object) -> list[str]:
    """Normalise PaddleOCR 3.x result objects/dicts into plain text lines."""
    texts: list[str] = []
    data = result
    for attribute in ("json", "res"):
        getter = getattr(result, attribute, None)
        if getter is not None:
            data = getter() if callable(getter) else getter
            break
    if isinstance(result, dict):
        data = result
    if isinstance(data, dict):
        payload = data.get("res", data)
        if isinstance(payload, dict):
            values = payload.get("rec_texts") or payload.get("texts") or []
            texts.extend(str(v) for v in values if v)
    elif isinstance(data, list):
        for item in data:
            texts.extend(_texts_from_result(item))
    return texts
