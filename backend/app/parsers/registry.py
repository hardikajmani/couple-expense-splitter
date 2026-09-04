"""Registry of available bank parsers.

To add support for a new bank: implement a ``BaseParser`` subclass in its own
module and register an instance here. The registry tries each parser's
``sniff`` in order and uses the first one that claims to understand the file.
"""
from __future__ import annotations

from typing import List, Tuple

from app.models import RawTransaction
from app.parsers.base import BaseParser, UnsupportedCsvError
from app.parsers.scotiabank import ScotiabankParser

_PARSERS: List[BaseParser] = [
    ScotiabankParser(),
]


def parse_statement(content: str, filename: str) -> Tuple[List[RawTransaction], str, str]:
    """Detect the right parser and parse the statement.

    Returns (transactions, account_type, bank_name).
    """
    header, _ = BaseParser._read_rows(content)
    for parser in _PARSERS:
        if parser.sniff(filename, header):
            transactions, account_type = parser.parse(content, filename)
            return transactions, account_type, parser.bank_name
    raise UnsupportedCsvError(
        "Could not detect a supported bank/statement format for this CSV. "
        "Supported banks: " + ", ".join(p.bank_name for p in _PARSERS)
    )
