"""Base parser interface + account/bank detection utilities.

Every bank-specific parser should subclass ``BaseParser`` and implement
``sniff`` (to decide whether it can handle a given CSV) and ``parse`` (to turn
the raw CSV text into a list of ``RawTransaction`` plus the detected account
type). This keeps bank-specific quirks isolated so that adding support for a
new bank in the future only requires adding a new parser module + registering
it, without touching the cleaning/categorization/calculation pipeline.
"""
from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from typing import List, Tuple

from app.models import RawTransaction

CREDIT_KEYWORDS = ("credit", "card", "visa", "mastercard")
CHEQUING_KEYWORDS = ("chequing", "checking", "debit")
SAVINGS_KEYWORDS = ("saving",)


class UnsupportedCsvError(ValueError):
    """Raised when no parser can understand a given CSV file."""


def detect_account_type(filename: str, header: List[str]) -> str:
    """Best-effort detection of statement/account type from filename + header."""
    haystack = (filename or "").lower() + " " + " ".join(h.lower() for h in header)
    if any(k in haystack for k in CREDIT_KEYWORDS):
        return "credit"
    if any(k in haystack for k in CHEQUING_KEYWORDS):
        return "chequing"
    if any(k in haystack for k in SAVINGS_KEYWORDS):
        return "savings"
    return "unknown"


class BaseParser(ABC):
    """Base class for all bank-specific CSV parsers."""

    bank_name: str = "generic"

    @abstractmethod
    def sniff(self, filename: str, header: List[str]) -> bool:
        """Return True if this parser understands the given CSV schema."""

    @abstractmethod
    def parse(self, content: str, filename: str) -> Tuple[List[RawTransaction], str]:
        """Parse CSV text into (transactions, account_type)."""

    @staticmethod
    def _read_rows(content: str) -> Tuple[List[str], List[dict]]:
        reader = csv.reader(io.StringIO(content))
        rows = [r for r in reader if any(cell.strip() for cell in r)]
        if not rows:
            raise UnsupportedCsvError("CSV file is empty")
        header = [h.strip() for h in rows[0]]
        dict_rows = []
        for row in rows[1:]:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            dict_rows.append({header[i]: row[i].strip() for i in range(len(header))})
        return header, dict_rows

    @staticmethod
    def _to_decimal(value: str) -> Decimal:
        cleaned = (value or "").replace(",", "").replace("$", "").strip()
        if cleaned in ("", "-"):
            return Decimal("0")
        negative = False
        if cleaned.startswith("(") and cleaned.endswith(")"):
            negative = True
            cleaned = cleaned[1:-1]
        try:
            dec = Decimal(cleaned)
        except InvalidOperation as exc:
            raise UnsupportedCsvError(f"Could not parse amount: {value!r}") from exc
        return -dec if negative else dec
