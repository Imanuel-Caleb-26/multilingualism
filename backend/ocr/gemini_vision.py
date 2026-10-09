"""
Google Gemini Vision OCR engine — uses the new google-genai SDK.

Required env var:
  GOOGLE_API_KEY  – from https://aistudio.google.com/app/apikey

Uses gemini-2.0-flash for speed or gemini-1.5-pro for best accuracy.
The model is prompted to act as a specialized manuscript transcription assistant.
"""
from __future__ import annotations

import os
import time
import logging
import re

from .base import BaseOCREngine, OCRResult, TextBlock

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert manuscript transcriptionist specialising in ancient and historical texts.
Your task is to perform accurate OCR on the provided manuscript image.

Instructions:
1. Transcribe ALL visible text exactly as it appears, preserving original spelling and diacritics.
2. Number each line of text as it appears on the page.
3. For unclear characters use [?] and for completely illegible sections use [illegible].
4. Note the script/language if identifiable (e.g. Devanagari, Latin, Sanskrit, Arabic, Greek).
5. Provide a confidence score (0.0–1.0) for each line based on legibility.

Respond ONLY with valid JSON in this exact format (no markdown fences):
{
  "language_detected": "<ISO 639-1 code or script name>",
  "overall_confidence": <float 0.0-1.0>,
  "lines": [
    {"line_number": 1, "text": "<transcribed text>", "confidence": <float>},
    ...
  ]
}"""


class GeminiVisionEngine(BaseOCREngine):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._model_name = model
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import google.genai as genai  # type: ignore
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return None
            self._client = genai.Client(api_key=api_key)
            return self._client
        except Exception as exc:
            logger.warning("Gemini client init failed: %s", exc)
            return None

    async def is_available(self) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY")) and self._get_client() is not None

    async def process(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        import json
        from google.genai import types as genai_types  # type: ignore
        from PIL import Image
        import io

        t0 = time.monotonic()
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini client is not initialised — set GOOGLE_API_KEY")

        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        prompt = (
            "Perform OCR on this manuscript image and return the JSON response as instructed. "
            "Be thorough and transcribe every line of text you can see."
        )

        response = client.models.generate_content(
            model=self._model_name,
            contents=[prompt, pil_image],
            config=genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
            ),
        )
        raw_text = response.text.strip()

        # Strip any accidental markdown fences
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

        data = json.loads(raw_text)

        blocks: list[TextBlock] = []
        for line in data.get("lines", []):
            blocks.append(
                TextBlock(
                    text=line.get("text", ""),
                    confidence=float(line.get("confidence", 0.8)),
                    line_number=int(line.get("line_number", len(blocks) + 1)),
                )
            )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        full_text = self._blocks_to_full_text(blocks)

        return OCRResult(
            engine=self.name,
            page=page,
            blocks=blocks,
            full_text=full_text,
            avg_confidence=float(data.get("overall_confidence", self._avg_confidence(blocks))),
            language_detected=data.get("language_detected"),
            processing_time_ms=elapsed_ms,
            raw_response=data,
        )
