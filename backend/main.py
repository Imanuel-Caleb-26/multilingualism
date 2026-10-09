# pyrefly: ignore [missing-import]
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env before importing OCR modules so env vars are available at init time
load_dotenv()

from ocr.router import get_available_engines  # noqa: E402
from api.routers.ocr import router as ocr_router
from api.routers.translation import router as translation_router
from api.routers.export import router as export_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(name)s │ %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Antiqua Lens API starting up…")
    engines = await get_available_engines()
    for e in engines:
        status = "✅ ready" if e["available"] else "❌ not configured"
        logger.info("  OCR engine %-14s %s", e["name"], status)
    yield
    logger.info("Antiqua Lens API shutting down.")


app = FastAPI(
    title="Antiqua Lens API",
    description="Ancient Manuscript OCR & Translation — multi-engine OCR pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Antiqua Lens API", "version": "1.0.0"}


app.include_router(ocr_router)
app.include_router(translation_router)
app.include_router(export_router)
