"""
OCR Router – selects and runs OCR engines based on configuration.

Priority / fallback logic:
  - OCR_ENGINE=auto  → try engines in order defined by OCR_ENGINE_PRIORITY
  - OCR_ENGINE=gemini | transkribus → use that engine only

The router also handles PDF-to-image conversion before passing images to engines.
"""
from __future__ import annotations

import os
import io
import logging
from typing import Optional

from .base import BaseOCREngine, OCRResult
from .gemini_vision import GeminiVisionEngine
from .transkribus import TranskribusEngine

logger = logging.getLogger(__name__)

# Singleton instances
_ENGINES: dict[str, BaseOCREngine] = {
    "gemini": GeminiVisionEngine(),
    "transkribus": TranskribusEngine(),
}


def _get_priority_list() -> list[str]:
    raw = os.getenv("OCR_ENGINE_PRIORITY", "transkribus,gemini")
    return [e.strip() for e in raw.split(",") if e.strip() in _ENGINES]


async def get_available_engines() -> list[dict]:
    """Return availability status for all engines."""
    result = []
    for name, engine in _ENGINES.items():
        available = await engine.is_available()
        result.append({"name": name, "available": available})
    return result


async def run_ocr(
    image_bytes: bytes,
    page: int = 1,
    engine: Optional[str] = None,
    filename: str = "",
) -> OCRResult:
    """
    Run OCR on image_bytes. If filename ends in .pdf, convert first page to image.

    Parameters
    ----------
    image_bytes : raw file bytes (image or PDF)
    page       : page number (informational)
    engine     : override engine; if None, reads OCR_ENGINE env var
               Available engines: gemini | transkribus
    filename   : original filename, used to detect PDF
    """
    # PDF → image
    image_bytes = await _pdf_to_image_if_needed(image_bytes, filename)

    engine_name = engine or os.getenv("OCR_ENGINE", "auto")

    if engine_name == "auto":
        return await _run_auto(image_bytes, page)
    
    if engine_name not in _ENGINES:
        raise ValueError(f"Unknown OCR engine: '{engine_name}'. Choose from: gemini, transkribus")
    
    selected = _ENGINES[engine_name]
    if not await selected.is_available():
        raise RuntimeError(
            f"OCR engine '{engine_name}' is not available. "
            "Check your credentials / environment variables."
        )
    return await selected.process(image_bytes, page)


async def _run_auto(image_bytes: bytes, page: int) -> OCRResult:
    """Try engines in priority order, return first success."""
    priority = _get_priority_list()
    last_error: Exception = RuntimeError("No OCR engines configured")

    for name in priority:
        engine = _ENGINES[name]
        try:
            if not await engine.is_available():
                logger.info("OCR engine '%s' not available, skipping", name)
                continue
            logger.info("Trying OCR engine: %s", name)
            result = await engine.process(image_bytes, page)
            logger.info("OCR succeeded with engine: %s (confidence=%.2f)", name, result.avg_confidence)
            return result
        except Exception as exc:
            logger.warning("OCR engine '%s' failed: %s", name, exc)
            last_error = exc

    # All engines failed – raise last error
    raise last_error


async def _pdf_to_image_if_needed(data: bytes, filename: str) -> bytes:
    """Convert first page of PDF to PNG bytes if input is a PDF."""
    if not filename.lower().endswith(".pdf"):
        return data
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        images = convert_from_bytes(data, first_page=1, last_page=1, dpi=300)
        if not images:
            raise ValueError("PDF conversion produced no pages")
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        logger.warning("pdf2image not available; sending raw PDF bytes to OCR engine")
        return data
    except Exception as exc:
        logger.warning("PDF conversion failed: %s — sending raw bytes", exc)
        return data
