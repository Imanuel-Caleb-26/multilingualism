import asyncio
import logging
from fastapi import APIRouter, HTTPException, Response
from api.schemas import TranslationResponse
from export import generate_bilingual_pdf

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/export/pdf", tags=["Export"])
async def export_to_pdf(body: TranslationResponse):
    """
    Generate a bilingual PDF document containing the original text, transliteration,
    and translation. Suitable for downloading or printing.
    """
    try:
        # Run PDF generation in thread pool to avoid blocking the event loop
        pdf_bytes = await asyncio.to_thread(
            generate_bilingual_pdf,
            body.source_text,
            body.model_dump()
        )
        return Response(
            content=bytes(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="antiqua-lens-translation.pdf"'
            }
        )
    except Exception as exc:
        logger.exception("Unexpected PDF generation error")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")
