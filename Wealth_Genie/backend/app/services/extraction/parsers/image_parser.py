from __future__ import annotations

import cv2
import numpy as np
import pytesseract

from app.services.extraction.base_parser import BaseParser, RawExtractionResult
from app.services.extraction.enums import ExtractionError
from app.services.extraction.parsers.ocr_preprocessing import preprocess_for_ocr


class ImageParser(BaseParser):
    """OCR parser for standalone image uploads (e.g. photographed salary slips)."""

    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        try:
            image_array = np.frombuffer(file_bytes, dtype=np.uint8)
            image_bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if image_bgr is None:
                raise ExtractionError("Could not decode image bytes")

            preprocessed = preprocess_for_ocr(image_bgr)
            text = pytesseract.image_to_string(preprocessed)
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"Failed to OCR image: {exc}") from exc

        return RawExtractionResult(raw_text=text, page_count=1, used_ocr=True)
