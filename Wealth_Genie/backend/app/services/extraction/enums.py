from enum import Enum


class DocumentKind(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"
    CSV = "csv"
    EXCEL = "excel"


class UnsupportedDocumentError(ValueError):
    """Raised when a file extension/content cannot be classified into a DocumentKind."""


class ExtractionError(RuntimeError):
    """Raised when a parser cannot extract usable content from a file."""
