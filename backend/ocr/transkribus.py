"""
Transkribus OCR Engine via the Transkribus REST API (CITlab/HTR+).

Transkribus specialises in historical handwritten and printed manuscripts.
Uses the publicly available REST API v1.

Required env vars:
  TRANSKRIBUS_USERNAME  – your Transkribus account email
  TRANSKRIBUS_PASSWORD  – your Transkribus account password
  TRANSKRIBUS_COLLECTION_ID  – (optional) collection to upload pages to; defaults to first writable collection

Transkribus flow:
  1. Login → get session token
  2. Upload image to a temp collection
  3. Submit HTR+ job (or classic ATR)
  4. Poll until complete
  5. Download PAGE XML result, parse into TextBlocks
"""
from __future__ import annotations

import os
import time
import logging
import asyncio
import io
import base64
from xml.etree import ElementTree as ET

import httpx

from .base import BaseOCREngine, BoundingBox, OCRResult, TextBlock

logger = logging.getLogger(__name__)

_BASE_URL = "https://transkribus.eu/TrpServer/rest"
_TIMEOUT = 60.0


class TranskribusEngine(BaseOCREngine):
    name = "transkribus"

    def __init__(self) -> None:
        self._session_id: str | None = None
        self._session_expires: float = 0.0

    # ── Authentication ────────────────────────────────────────────────────────

    async def _login(self) -> str:
        """Login and return session ID."""
        username = os.getenv("TRANSKRIBUS_USERNAME", "")
        password = os.getenv("TRANSKRIBUS_PASSWORD", "")
        if not username or not password:
            raise RuntimeError("TRANSKRIBUS_USERNAME and TRANSKRIBUS_PASSWORD must be set")

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_BASE_URL}/auth/login",
                data={"user": username, "pw": password},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._session_id = data["sessionId"]
            self._session_expires = time.monotonic() + 3600  # sessions last ~1h
            return self._session_id

    async def _get_session(self) -> str:
        if self._session_id is None or time.monotonic() > self._session_expires:
            await self._login()
        return self._session_id  # type: ignore[return-value]

    def _auth_headers(self, session_id: str) -> dict:
        return {"Cookie": f"JSESSIONID={session_id}", "Accept": "application/json"}

    # ── Availability ──────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        username = os.getenv("TRANSKRIBUS_USERNAME", "")
        password = os.getenv("TRANSKRIBUS_PASSWORD", "")
        if not username or not password:
            return False
        try:
            await self._login()
            return True
        except Exception as exc:
            logger.warning("Transkribus availability check failed: %s", exc)
            return False

    # ── Core processing ───────────────────────────────────────────────────────

    async def process(self, image_bytes: bytes, page: int = 1) -> OCRResult:
        t0 = time.monotonic()
        session = await self._get_session()
        headers = self._auth_headers(session)

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # 1. Get/create a temp collection
            col_id = os.getenv("TRANSKRIBUS_COLLECTION_ID") or await self._get_or_create_collection(client, headers)

            # 2. Create a new document in the collection
            doc_id = await self._upload_image(client, headers, col_id, image_bytes, page)

            # 3. Trigger HTR+ recognition job
            job_id = await self._run_htr(client, headers, col_id, doc_id)

            # 4. Poll until complete (max 120s)
            await self._wait_for_job(client, headers, job_id, max_wait=120)

            # 5. Fetch PAGE XML and parse
            page_xml = await self._fetch_page_xml(client, headers, col_id, doc_id, page_num=1)

        blocks = self._parse_page_xml(page_xml)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        return OCRResult(
            engine=self.name,
            page=page,
            blocks=blocks,
            full_text=self._blocks_to_full_text(blocks),
            avg_confidence=self._avg_confidence(blocks),
            processing_time_ms=elapsed_ms,
        )

    # ── Helper steps ──────────────────────────────────────────────────────────

    async def _get_or_create_collection(self, client: httpx.AsyncClient, headers: dict) -> str:
        resp = await client.get(f"{_BASE_URL}/collections/list", headers=headers)
        resp.raise_for_status()
        cols = resp.json()
        if cols:
            return str(cols[0]["colId"])
        # Create one
        resp2 = await client.post(
            f"{_BASE_URL}/collections/createCollection",
            params={"collName": "AntiquaLens_Temp"},
            headers=headers,
        )
        resp2.raise_for_status()
        return str(resp2.json())

    async def _upload_image(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        col_id: str,
        image_bytes: bytes,
        page: int,
    ) -> str:
        from PIL import Image
        import io as _io

        # Convert to JPEG for upload efficiency
        img = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        jpeg_bytes = buf.getvalue()

        # Create doc
        resp = await client.post(
            f"{_BASE_URL}/collections/{col_id}/upload",
            params={"fileName": f"page_{page:03d}.jpg"},
            content=jpeg_bytes,
            headers={**headers, "Content-Type": "image/jpeg"},
        )
        resp.raise_for_status()
        return str(resp.json()["docId"])

    async def _run_htr(self, client: httpx.AsyncClient, headers: dict, col_id: str, doc_id: str) -> str:
        """Submit an HTR+ job using the default public model."""
        payload = {
            "docList": {"docs": [{"docId": doc_id, "pageList": {"pages": [{"pageNr": 1}]}}]},
            "params": {"dict": "None", "batchSize": 5, "beamWidth": 2, "doLinePolygons": False},
        }
        resp = await client.post(
            f"{_BASE_URL}/recognition/{col_id}/htrResult",
            json=payload,
            headers={**headers, "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return str(resp.json())

    async def _wait_for_job(self, client: httpx.AsyncClient, headers: dict, job_id: str, max_wait: int = 120):
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            resp = await client.get(f"{_BASE_URL}/jobs/{job_id}", headers=headers)
            resp.raise_for_status()
            job = resp.json()
            state = job.get("state", "")
            if state == "FINISHED":
                return
            if state in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"Transkribus job {job_id} ended with state: {state}")
            await asyncio.sleep(3)
        raise TimeoutError(f"Transkribus job {job_id} did not finish within {max_wait}s")

    async def _fetch_page_xml(
        self, client: httpx.AsyncClient, headers: dict, col_id: str, doc_id: str, page_num: int
    ) -> str:
        resp = await client.get(
            f"{_BASE_URL}/collections/{col_id}/{doc_id}/{page_num}/text",
            headers={**headers, "Accept": "application/xml"},
        )
        resp.raise_for_status()
        return resp.text

    # ── PAGE XML Parser ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_page_xml(xml_text: str) -> list[TextBlock]:
        """Parse Transkribus PAGE XML into TextBlocks."""
        NS = {"p": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"}
        root = ET.fromstring(xml_text)
        blocks: list[TextBlock] = []
        line_num = 0

        for text_line in root.findall(".//p:TextLine", NS):
            line_num += 1
            text_equiv = text_line.find("p:TextEquiv", NS)
            unicode_el = text_equiv.find("p:Unicode", NS) if text_equiv is not None else None
            text = unicode_el.text or "" if unicode_el is not None else ""

            # Confidence
            conf = float(text_equiv.get("conf", "0.8")) if text_equiv is not None else 0.8

            # Bounding box from Coords
            coords_el = text_line.find("p:Coords", NS)
            bbox: BoundingBox | None = None
            if coords_el is not None:
                points_str = coords_el.get("points", "")
                if points_str:
                    pts = [tuple(map(int, p.split(","))) for p in points_str.split()]
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    bbox = BoundingBox(
                        x=min(xs),
                        y=min(ys),
                        width=max(xs) - min(xs),
                        height=max(ys) - min(ys),
                    )

            if text.strip():
                blocks.append(
                    TextBlock(
                        text=text.strip(),
                        confidence=conf,
                        line_number=line_num,
                        bounding_box=bbox,
                    )
                )

        return blocks
