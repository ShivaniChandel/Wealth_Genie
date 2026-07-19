"""
BaseParser: the contract every document-type parser implements.

Parsers are strictly deterministic and never call any AI provider. They only
turn bytes into raw text (and, for tabular formats, structured rows). The
LLM-based structuring step happens later, in UniversalExtractor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawExtractionResult:
    raw_text: str
    tables: Optional[List[dict]] = field(default=None)
    page_count: Optional[int] = None
    used_ocr: bool = False


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_bytes: bytes) -> RawExtractionResult:
        raise NotImplementedError
