import io
import json

import fitz
import pandas as pd
import pytest

from app.services.extraction.detector import DocumentDetector
from app.services.extraction.enums import DocumentKind, UnsupportedDocumentError
from app.services.extraction.normalizer import TextNormalizer
from app.services.extraction.parsers.csv_parser import CsvParser
from app.services.extraction.parsers.digital_pdf_parser import DigitalPdfParser
from app.services.extraction.registry import ParserRegistry
from app.services.extraction.validator import FinancialJsonValidationError, validate_financial_json
from app.services.extraction.universal_extractor import UniversalExtractor
from app.services.llm.base import LLMProvider


# ---------- Fixtures ----------

def _make_digital_pdf_bytes(
    text: str = "Statement Period: Jan 2026\nAccount Balance: 1000.00\nBank: Test National Bank"
) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _make_blank_pdf_bytes() -> bytes:
    """A PDF with a page but no text layer -> should classify as scanned."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class _StubLLMProvider(LLMProvider):
    def __init__(self, response: dict):
        self._response = response

    async def extract_financial_json(self, normalized_text: str, document_type: str) -> dict:
        return self._response


# ---------- DocumentDetector ----------

def test_detector_classifies_digital_pdf():
    detector = DocumentDetector()
    kind = detector.detect(_make_digital_pdf_bytes(), "statement.pdf")
    assert kind == DocumentKind.DIGITAL_PDF


def test_detector_classifies_blank_pdf_as_scanned():
    detector = DocumentDetector(text_threshold_chars=50)
    kind = detector.detect(_make_blank_pdf_bytes(), "scan.pdf")
    assert kind == DocumentKind.SCANNED_PDF


def test_detector_classifies_csv():
    detector = DocumentDetector()
    kind = detector.detect(b"a,b,c\n1,2,3", "export.csv")
    assert kind == DocumentKind.CSV


def test_detector_classifies_image():
    detector = DocumentDetector()
    kind = detector.detect(b"\x89PNG\r\n", "photo.png")
    assert kind == DocumentKind.IMAGE


def test_detector_rejects_unsupported_extension():
    detector = DocumentDetector()
    with pytest.raises(UnsupportedDocumentError):
        detector.detect(b"whatever", "notes.docx")


# ---------- TextNormalizer ----------

def test_normalizer_collapses_whitespace_and_control_chars():
    normalizer = TextNormalizer()
    raw = "Hello    world\x00\n\n\n\nBye   there"
    result = normalizer.normalize(raw)
    assert "\x00" not in result
    assert "    " not in result
    assert "\n\n\n" not in result


def test_normalizer_handles_empty_string():
    assert TextNormalizer().normalize("") == ""


# ---------- Parsers ----------

def test_digital_pdf_parser_extracts_text():
    parser = DigitalPdfParser()
    result = parser.parse(_make_digital_pdf_bytes("Balance: 5000"))
    assert "Balance" in result.raw_text
    assert result.used_ocr is False
    assert result.page_count == 1


def test_csv_parser_extracts_rows():
    df = pd.DataFrame({"description": ["Coffee", "Rent"], "amount": [4.5, 1200]})
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    file_bytes = buf.getvalue().encode("utf-8")

    parser = CsvParser()
    result = parser.parse(file_bytes)
    assert result.tables is not None
    assert len(result.tables) == 2
    assert result.tables[0]["description"] == "Coffee"


# ---------- ParserRegistry ----------

def test_registry_returns_correct_parser_type():
    registry = ParserRegistry()
    parser = registry.get_parser(DocumentKind.DIGITAL_PDF)
    assert isinstance(parser, DigitalPdfParser)


def test_registry_raises_for_unregistered_kind():
    registry = ParserRegistry()
    registry._PARSERS = {}  # simulate a kind with no registered parser
    with pytest.raises(ValueError):
        registry.get_parser(DocumentKind.DIGITAL_PDF)


# ---------- Validator ----------

def test_validate_financial_json_accepts_minimal_valid_payload():
    profile = validate_financial_json({
        "user": {},
        "accounts": [],
        "transactions": [],
        "loans": [],
        "credit_cards": [],
        "summary": {},
        "recommendations": [],
    })
    assert profile.accounts == []
    assert profile.summary.total_monthly_income is None


def test_validate_financial_json_accepts_populated_payload():
    profile = validate_financial_json({
        "user": {"name": "Jane Doe"},
        "accounts": [{
            "account_id": "acc-1", "bank_name": "Test Bank", "account_type": "savings",
            "currency": "USD", "opening_balance": 100, "closing_balance": 200,
        }],
        "transactions": [],
        "loans": [],
        "credit_cards": [],
        "summary": {"total_monthly_income": 5000},
        "recommendations": [{
            "agent": "debt_agent", "priority": "high", "title": "Pay off card",
            "detail": "High interest rate detected",
        }],
    })
    assert profile.accounts[0].bank_name == "Test Bank"
    assert profile.recommendations[0].priority == "high"


def test_validate_financial_json_rejects_invalid_enum_value():
    with pytest.raises(FinancialJsonValidationError):
        validate_financial_json({
            "accounts": [{"account_type": "not-a-real-type"}],
        })


# ---------- UniversalExtractor (orchestrator, mocked LLM) ----------

@pytest.mark.asyncio
async def test_universal_extractor_end_to_end_with_stub_llm():
    stub_response = {
        "user": {},
        "accounts": [],
        "transactions": [],
        "loans": [],
        "credit_cards": [],
        "summary": {"total_monthly_income": 6000},
        "recommendations": [],
    }
    extractor = UniversalExtractor(llm_provider=_StubLLMProvider(stub_response))

    outcome = await extractor.extract(
        file_bytes=_make_digital_pdf_bytes("Net Pay: 6000.00\nEmployee: Jane Doe\nPay Period: January 2026"),
        filename="salary_slip.pdf",
        document_type="salary_slip",
    )

    assert outcome.document_kind == DocumentKind.DIGITAL_PDF
    assert outcome.used_ocr is False
    assert outcome.profile.summary.total_monthly_income == 6000
