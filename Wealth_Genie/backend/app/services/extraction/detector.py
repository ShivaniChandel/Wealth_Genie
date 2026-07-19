"""
DocumentDetector.

Deterministic, provider-independent classification of an uploaded file into a
DocumentKind. For PDFs specifically, this is what enforces the rule
"never OCR a searchable PDF": we sample the first few pages with PyMuPDF and
only fall back to scanned-PDF (OCR) handling if extractable text is below a
threshold.
"""
from __future__ import annotations

import os

import fitz  # PyMuPDF

from app.config import settings
from app.services.extraction.enums import DocumentKind, UnsupportedDocumentError

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
_PDF_SAMPLE_PAGES = 3


class DocumentDetector:
    def __init__(self, text_threshold_chars: int | None = None):
        self._text_threshold_chars = text_threshold_chars or settings.OCR_TEXT_THRESHOLD_CHARS

    def detect(self, file_bytes: bytes, filename: str) -> DocumentKind:
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".csv":
            return DocumentKind.CSV
        if ext in (".xls", ".xlsx"):
            return DocumentKind.EXCEL
        if ext in _IMAGE_EXTENSIONS:
            return DocumentKind.IMAGE
        if ext == ".pdf":
            return self._classify_pdf(file_bytes)

        raise UnsupportedDocumentError(f"Unsupported file extension: '{ext}'")

    def _classify_pdf(self, file_bytes: bytes) -> DocumentKind:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            pages_to_sample = min(_PDF_SAMPLE_PAGES, doc.page_count)
            extracted_chars = 0
            for page_index in range(pages_to_sample):
                page = doc.load_page(page_index)
                extracted_chars += len(page.get_text("text").strip())

        if extracted_chars >= self._text_threshold_chars:
            return DocumentKind.DIGITAL_PDF
        return DocumentKind.SCANNED_PDF
