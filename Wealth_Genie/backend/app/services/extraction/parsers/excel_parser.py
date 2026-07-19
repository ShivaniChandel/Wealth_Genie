from __future__ import annotations

import io

import pandas as pd

from app.services.extraction.base_parser import BaseParser, RawExtractionResult
from app.services.extraction.enums import ExtractionError


class ExcelParser(BaseParser):
    """Deterministic tabular extraction for .xls/.xlsx uploads. Reads the first sheet."""

    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0)
        except Exception as exc:
            raise ExtractionError(f"Failed to parse Excel file: {exc}") from exc

        records = df.to_dict(orient="records")
        raw_text = df.to_csv(index=False)

        return RawExtractionResult(raw_text=raw_text, tables=records, used_ocr=False)
