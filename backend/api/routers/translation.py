import asyncio
import logging
from fastapi import APIRouter, HTTPException
from api.schemas import TranslationRequest, TranslationResponse
from translation import GeminiTranslator

logger = logging.getLogger(__name__)
router = APIRouter()

_translator = GeminiTranslator()

@router.post("/translate", response_model=TranslationResponse, tags=["Translation"])
async def translate_text(body: TranslationRequest):
    """
    Translate OCR'd manuscript text using the Gemini language model.

    Accepts the (possibly edited) transcription from the OCR stage and returns:
    - Transliteration (IAST / romanised)
    - Literal & readable English translations
    - Scholarly translator notes
    - Confidence score and review status
    """
    if not body.source_text.strip():
        raise HTTPException(status_code=400, detail="source_text must not be empty")

    if not _translator.is_available():
        raise HTTPException(
            status_code=503,
            detail="Translation engine unavailable — set GOOGLE_API_KEY in .env",
        )

    try:
        result = await asyncio.to_thread(
            _translator.translate,
            body.source_text,
            body.language_hint,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected translation error")
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}")

    return result
