"""
Shared models and base class for all OCR engines.
"""
from __future__ import annotations

import io
import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class TextBlock:
    text: str
    confidence: float          # 0.0 – 1.0
    line_number: int
    bounding_box: Optional[BoundingBox] = None
    language_hint: Optional[str] = None   # e.g. "sa" (Sanskrit), "la" (Latin)


@dataclass
class OCRResult:
    engine: str                            # which engine produced this
    page: int
    blocks: list[TextBlock] = field(default_factory=list)
    full_text: str = ""
    avg_confidence: float = 0.0
    language_detected: Optional[str] = None
    processing_time_ms: int = 0
    raw_response: Optional[dict] = None   # engine-specific raw data

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "page": self.page,
            "full_text": self.full_text,
            "avg_confidence": self.avg_confidence,
            "language_detected": self.language_detected,
            "processing_time_ms": self.processing_time_ms,
            "blocks": [
                {
                    "text": b.text,
                    "confidence": b.confidence,
                    "line_number": b.line_number,
                    "bounding_box": (
                        {
                            "x": b.bounding_box.x,
                            "y": b.bounding_box.y,
                            "width": b.bounding_box.width,
                            "height": b.bounding_box.height,
                        }
                        if b.bounding_box
                        else None
                    ),
                    "language_hint": b.language_hint,
                }
                for b in self.blocks
            ],
        }


class BaseOCREngine(ABC):
    """Abstract base class every OCR engine must implement."""

    name: str = "base"

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if the engine is configured and reachable."""
        ...

    @abstractmethod
    async def process(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        """Run OCR on raw image bytes and return a structured result."""
        ...

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_base64(image_bytes: bytes, fmt: str = "PNG") -> str:
        """Encode raw image bytes as base64 (optionally re-encode format)."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def _avg_confidence(blocks: list[TextBlock]) -> float:
        if not blocks:
            return 0.0
        return round(sum(b.confidence for b in blocks) / len(blocks), 4)

    @staticmethod
    def _blocks_to_full_text(blocks: list[TextBlock]) -> str:
        return "\n".join(b.text for b in blocks if b.text.strip())
