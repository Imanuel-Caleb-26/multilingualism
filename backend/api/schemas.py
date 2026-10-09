from typing import Optional
from pydantic import BaseModel

class BoundingBoxModel(BaseModel):
    x: int
    y: int
    width: int
    height: int

class TextBlockModel(BaseModel):
    text: str
    confidence: float
    line_number: int
    bounding_box: BoundingBoxModel | None = None
    language_hint: str | None = None

class OCRResponse(BaseModel):
    engine: str
    page: int
    full_text: str
    avg_confidence: float
    language_detected: str | None = None
    processing_time_ms: int
    blocks: list[TextBlockModel]

class EngineStatus(BaseModel):
    name: str
    available: bool

class TranslationRequest(BaseModel):
    source_text: str
    language_hint: Optional[str] = None

class TranslationResponse(BaseModel):
    segment_id: str
    source_text: str
    language_detected: Optional[str] = None
    transliteration: str
    literal_translation: str
    readable_translation: str
    translator_notes: list[str]
    confidence: float
    review_status: str
    processing_time_ms: int
