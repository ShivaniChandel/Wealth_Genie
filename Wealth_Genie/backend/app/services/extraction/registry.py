"""
ParserRegistry: Factory Pattern.

Maps a DocumentKind to the BaseParser implementation responsible for it.
Adding a new supported input type means adding one parser class and one
line here — nothing else in the extraction pipeline changes.
"""
from __future__ import annotations

from typing import Dict, Type

from app.services.extraction.base_parser import BaseParser
from app.services.extraction.enums import DocumentKind
from app.services.extraction.parsers.csv_parser import CsvParser
from app.services.extraction.parsers.digital_pdf_parser import DigitalPdfParser
from app.services.extraction.parsers.excel_parser import ExcelParser
from app.services.extraction.parsers.image_parser import ImageParser
from app.services.extraction.parsers.scanned_pdf_parser import ScannedPdfParser


class ParserRegistry:
    _PARSERS: Dict[DocumentKind, Type[BaseParser]] = {
        DocumentKind.DIGITAL_PDF: DigitalPdfParser,
        DocumentKind.SCANNED_PDF: ScannedPdfParser,
        DocumentKind.IMAGE: ImageParser,
        DocumentKind.CSV: CsvParser,
        DocumentKind.EXCEL: ExcelParser,
    }

    def get_parser(self, kind: DocumentKind) -> BaseParser:
        parser_cls = self._PARSERS.get(kind)
        if parser_cls is None:
            raise ValueError(f"No parser registered for DocumentKind '{kind}'")
        return parser_cls()
