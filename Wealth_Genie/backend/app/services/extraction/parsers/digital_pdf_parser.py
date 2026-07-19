from __future__ import annotations

import fitz  # PyMuPDF

from app.services.extraction.base_parser import BaseParser, RawExtractionResult
from app.services.extraction.enums import ExtractionError


class DigitalPdfParser(BaseParser):
    """Extracts text directly from a searchable PDF. Never invokes OCR."""

    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                pages_text = [doc.load_page(i).get_text("text") for i in range(doc.page_count)]
                page_count = doc.page_count
        except Exception as exc:  # PyMuPDF raises its own RuntimeError subclasses
            raise ExtractionError(f"Failed to read digital PDF: {exc}") from exc

        return RawExtractionResult(
            raw_text="\n".join(pages_text),
            page_count=page_count,
            used_ocr=False,
        )
