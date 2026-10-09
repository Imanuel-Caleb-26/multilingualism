"""
Gemini Translation Engine for ancient manuscript text — uses the new google-genai SDK.

Required env var:
  GOOGLE_API_KEY – from https://aistudio.google.com/app/apikey

The translator takes raw OCR transcription and produces:
  - transliteration  (romanised form)
  - literal_translation
  - readable_translation
  - translator_notes  (list of scholarly observations)
  - detected_language / script
  - confidence score
"""
from __future__ import annotations

import os
import re
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_TRANSLATION_SYSTEM_PROMPT = """\
You are a world-class scholar specialising in ancient and historical manuscripts, \
with deep expertise in Sanskrit, Latin, Greek, Arabic, Pali, Aramaic, and other \
classical languages and scripts.

You will receive a raw OCR transcription of a manuscript page. Your task is to \
produce a scholarly translation with the following components:

1. **transliteration** – Romanised / IAST (or appropriate standard) transliteration \
   of the source text. If the text is already in Roman script, return it unchanged.
2. **literal_translation** – A word-for-word translation that preserves the \
   grammatical structure of the original.
3. **readable_translation** – A fluent, natural English translation that conveys \
   the meaning clearly for a modern reader.
4. **translator_notes** – A JSON array of scholarly notes. Each note should flag:
   - Uncertain or damaged words (e.g. "[?] may be 'dharma' or 'karma'")
   - Grammatical forms worth noting (e.g. "Line 3 uses the locative absolute")
   - Historical / cultural context clues
   - Script or orthographic observations
   Keep each note concise (1–2 sentences).
5. **language_detected** – The language/script of the source (e.g. "Sanskrit", \
   "Medieval Latin", "Koine Greek").
6. **confidence** – Your overall confidence in the translation (0.0–1.0).

Respond ONLY with valid JSON (no markdown fences) in this exact format:
{
  "language_detected": "<language or script name>",
  "transliteration": "<full romanised text>",
  "literal_translation": "<word-for-word English>",
  "readable_translation": "<fluent English translation>",
  "translator_notes": ["<note 1>", "<note 2>", ...],
  "confidence": <float 0.0-1.0>
}
"""


class GeminiTranslator:
    """Uses Gemini to translate ancient manuscript transcriptions."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._model_name = model
        self._client = None

    # ── Init ──────────────────────────────────────────────────────────────────

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
            logger.warning("GeminiTranslator init failed: %s", exc)
            return None

    def is_available(self) -> bool:
        return bool(os.getenv("GOOGLE_API_KEY")) and self._get_client() is not None

    # ── Core ──────────────────────────────────────────────────────────────────

    def translate(self, source_text: str, language_hint: Optional[str] = None) -> dict:
        """
        Translate manuscript text synchronously.

        Parameters
        ----------
        source_text   : Raw OCR text (may include [?] and [illegible] markers)
        language_hint : Optional detected language from OCR stage

        Returns dict with keys:
          segment_id, source_text, transliteration, literal_translation,
          readable_translation, translator_notes, review_status,
          language_detected, confidence, processing_time_ms
        """
        from google.genai import types as genai_types  # type: ignore

        t0 = time.monotonic()
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini translator is not initialised — set GOOGLE_API_KEY")

        hint_clause = f" The source language/script is likely {language_hint}." if language_hint else ""
        user_prompt = (
            f"Translate the following manuscript transcription.{hint_clause}\n\n"
            f"--- SOURCE TEXT ---\n{source_text}\n--- END ---"
        )

        response = client.models.generate_content(
            model=self._model_name,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=_TRANSLATION_SYSTEM_PROMPT,
            ),
        )
        raw = response.text.strip()

        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("Gemini translation JSON parse failed: %s\nRaw: %s", exc, raw[:500])
            raise RuntimeError(f"Translation model returned invalid JSON: {exc}") from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        confidence = float(data.get("confidence", 0.8))

        # Determine review status from confidence
        if confidence >= 0.85:
            review_status = "high_confidence"
        elif confidence >= 0.60:
            review_status = "needs_review"
        else:
            review_status = "low_confidence"

        return {
            "segment_id": "page_01",
            "source_text": source_text,
            "language_detected": data.get("language_detected", language_hint or "unknown"),
            "transliteration": data.get("transliteration", ""),
            "literal_translation": data.get("literal_translation", ""),
            "readable_translation": data.get("readable_translation", ""),
            "translator_notes": data.get("translator_notes", []),
            "confidence": confidence,
            "review_status": review_status,
            "processing_time_ms": elapsed_ms,
        }
