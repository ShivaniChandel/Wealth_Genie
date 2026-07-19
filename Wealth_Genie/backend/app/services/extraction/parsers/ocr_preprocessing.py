"""
Shared OpenCV preprocessing for OCR parsers (scanned PDFs and images).

Kept as a standalone module (Strategy-friendly) so preprocessing can evolve
(deskew, denoise) independently of which parser calls it.
"""
from __future__ import annotations

import cv2
import numpy as np


def preprocess_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
    """Grayscale + adaptive threshold to maximize Tesseract accuracy on
    photographed/scanned financial documents (varying lighting, low contrast)."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )
    return thresh
