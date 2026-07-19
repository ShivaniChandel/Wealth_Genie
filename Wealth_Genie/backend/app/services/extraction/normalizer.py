"""
TextNormalizer: cleans raw extracted text before it is handed to the LLM
structuring step. Purely deterministic string processing — no AI involved.
"""
from __future__ import annotations

import re
import unicodedata


class TextNormalizer:
    _MULTI_WHITESPACE_RE = re.compile(r"[ \t]{2,}")
    _MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
    _CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    def normalize(self, raw_text: str) -> str:
        if not raw_text:
            return ""

        text = unicodedata.normalize("NFKC", raw_text)
        text = self._CONTROL_CHARS_RE.sub("", text)
        text = self._MULTI_WHITESPACE_RE.sub(" ", text)
        text = self._MULTI_NEWLINE_RE.sub("\n\n", text)
        return text.strip()
