from __future__ import annotations

import shutil

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract

from app.config import settings
from app.services.extraction.base_parser import BaseParser, RawExtractionResult
from app.services.extraction.enums import ExtractionError
from app.services.extraction.parsers.ocr_preprocessing import preprocess_for_ocr

# Ensure pytesseract uses the installed Tesseract binary.
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

_RENDER_ZOOM = 2.0  # ~144 DPI


class ScannedPdfParser(BaseParser):
    """
    OCR parser for scanned/image PDFs.
    """

    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                page_count = doc.page_count
                pages_to_process = min(page_count, settings.MAX_OCR_PAGES)

                matrix = fitz.Matrix(_RENDER_ZOOM, _RENDER_ZOOM)
                page_texts = []

                for i in range(pages_to_process):
                    page = doc.load_page(i)
                    pixmap = page.get_pixmap(matrix=matrix)

                    image_bgr = self._pixmap_to_bgr(pixmap)
                    preprocessed = preprocess_for_ocr(image_bgr)

                    text = pytesseract.image_to_string(preprocessed)
                    page_texts.append(text)

        except Exception as exc:
            raise ExtractionError(
                f"{type(exc).__name__}: {exc}"
            ) from exc

        return RawExtractionResult(
            raw_text="\n".join(page_texts),
            page_count=page_count,
            used_ocr=True,
        )

    @staticmethod
    def _pixmap_to_bgr(pixmap: fitz.Pixmap) -> np.ndarray:
        img_array = np.frombuffer(
            pixmap.samples,
            dtype=np.uint8,
        ).reshape(
            pixmap.height,
            pixmap.width,
            pixmap.n,
        )

        if pixmap.n == 4:
            return cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)

        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)