from __future__ import annotations

import io

import pandas as pd

from app.services.extraction.base_parser import BaseParser, RawExtractionResult
from app.services.extraction.enums import ExtractionError


class CsvParser(BaseParser):
    """Deterministic tabular extraction for CSV exports (e.g. bank transaction exports)."""

    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception as exc:
            raise ExtractionError(f"Failed to parse CSV: {exc}") from exc

        records = df.to_dict(orient="records")
        # raw_text carries a human/LLM-readable rendering of the table so the
        # same normalization + LLM-structuring path used by text parsers applies.
        raw_text = df.to_csv(index=False)

        return RawExtractionResult(raw_text=raw_text, tables=records, used_ocr=False)
