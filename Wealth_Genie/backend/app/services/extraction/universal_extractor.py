"""
UniversalExtractor.

Pure orchestrator (Service Layer). Depends only on interfaces/injected
collaborators — never imports Supabase, FastAPI, or a concrete AI SDK
directly. This is what makes it independently testable and provider-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas_ext.financial import UniversalFinancialProfile
from app.services.extraction.detector import DocumentDetector
from app.services.extraction.enums import DocumentKind
from app.services.extraction.normalizer import TextNormalizer
from app.services.extraction.registry import ParserRegistry
from app.services.extraction.validator import validate_financial_json
from app.services.llm.base import LLMProvider


@dataclass
class ExtractionOutcome:
    profile: UniversalFinancialProfile
    document_kind: DocumentKind
    used_ocr: bool
    page_count: int | None


class UniversalExtractor:
    def __init__(
        self,
        llm_provider: LLMProvider,
        detector: DocumentDetector | None = None,
        registry: ParserRegistry | None = None,
        normalizer: TextNormalizer | None = None,
    ):
        self._llm_provider = llm_provider
        self._detector = detector or DocumentDetector()
        self._registry = registry or ParserRegistry()
        self._normalizer = normalizer or TextNormalizer()

    async def extract(
        self, file_bytes: bytes, filename: str, document_type: str
    ) -> ExtractionOutcome:
        kind = self._detector.detect(file_bytes, filename)
        parser = self._registry.get_parser(kind)
        raw_result = parser.parse(file_bytes)

        normalized_text = self._normalizer.normalize(raw_result.raw_text)

        raw_json = await self._llm_provider.extract_financial_json(
            normalized_text=normalized_text,
            document_type=document_type,
        )
        profile = validate_financial_json(raw_json)

        return ExtractionOutcome(
            profile=profile,
            document_kind=kind,
            used_ocr=raw_result.used_ocr,
            page_count=raw_result.page_count,
        )
