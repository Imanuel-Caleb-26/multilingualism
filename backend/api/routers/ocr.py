import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from api.schemas import EngineStatus, OCRResponse
# pyrefly: ignore [missing-import]
from ocr.router import run_ocr, get_available_engines

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/engines", response_model=list[EngineStatus], tags=["OCR"])
async def list_engines():
    """List all OCR engines and whether they are currently configured."""
    return await get_available_engines()

@router.post("/upload", tags=["Upload"])
async def upload_document(file: UploadFile = File(...)):
    """Accept a file upload and return metadata. Actual OCR is triggered separately."""
    content_type = file.content_type or ""
    allowed = {"image/jpeg", "image/png", "image/webp", "image/tiff", "application/pdf"}
    if content_type not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Supported: JPEG, PNG, WEBP, TIFF, PDF",
        )
    data = await file.read()
    size_kb = round(len(data) / 1024, 1)
    return {
        "filename": file.filename,
        "content_type": content_type,
        "size_kb": size_kb,
        "status": "uploaded",
    }

@router.post("/ocr/process", response_model=OCRResponse, tags=["OCR"])
async def process_ocr(
    file: UploadFile = File(...),
    page: int = Query(default=1, ge=1, description="Page number (for multi-page PDFs)"),
    engine: str = Query(
        default="auto",
        description="OCR engine: auto | gemini | transkribus",
    ),
):
    """
    Upload a manuscript image or PDF and run OCR.

    - **auto** mode tries engines in priority order (set via OCR_ENGINE_PRIORITY env var).
    - Returns structured text blocks with per-line confidence scores and bounding boxes.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        result = await run_ocr(
            image_bytes=data,
            page=page,
            engine=None if engine == "auto" else engine,
            filename=file.filename or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected OCR error")
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}")

    return result.to_dict()
