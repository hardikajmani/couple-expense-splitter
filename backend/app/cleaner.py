"""Statement cleaning: merchant-key normalization and transaction ID hashing.

``clean_statement`` turns the parser's ``RawTransaction`` list into
normalized ``Transaction`` objects with a stable ``transactionId`` (used for
idempotency / dedupe across re-uploads) and a cleaned ``merchantKey``.
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import List

from app.models import Transaction, RawTransaction

# Noise tokens that appear in raw bank descriptions but carry no merchant
# identity information.
_NOISE_WORDS = [
    r"\bPOS\b",
    r"\bPURCHASE\b",
    r"\bPAYMENT\b",
    r"\bDEBIT\b",
    r"\bCREDIT\b",
    r"\bRECURRING\b",
    r"\bPRE[- ]?AUTH\w*\b",
    r"\bWWW\b",
    r"\bTHE\b",
]

# Canadian province/territory abbreviations, often trailing a merchant city.
_PROVINCES = {
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
}


def clean_merchant(description: str) -> str:
    """Reduce a raw statement description down to a stable merchant key.

    Example: "POS PURCHASE WALMART #1234 WINNIPEG MB" -> "walmart"
    """
    text = description.upper()

    # Strip reference numbers, card numbers, dates typically embedded.
    text = re.sub(r"\b\d{2}/\d{2}(/\d{2,4})?\b", " ", text)  # dates
    text = re.sub(r"#\s*\d+", " ", text)  # #1234 style ids
    text = re.sub(r"\b[A-Z0-9]{0,3}\d{4,}[A-Z0-9]*\b", " ", text)  # long numeric/ref ids

    for pattern in _NOISE_WORDS:
        text = re.sub(pattern, " ", text)

    tokens = [t for t in re.split(r"[^A-Z0-9&]+", text) if t]

    # Drop a trailing province code and the city word(s) immediately before it
    # is hard to do reliably without a gazetteer, so we conservatively only
    # drop a trailing 2-letter province abbreviation and a single trailing
    # all-caps "city-like" token that precedes it.
    if tokens and tokens[-1] in _PROVINCES:
        tokens.pop()
        if len(tokens) > 1:
            tokens.pop()

    cleaned = " ".join(tokens).strip().lower()
    return cleaned or description.strip().lower()


def make_transaction_id(date: str, amount: Decimal, description: str, account_name: str, spender: str) -> str:
    """Stable hash used as the transactionId for idempotency/dedupe."""
    payload = "|".join([date, str(amount), description.strip().lower(), account_name, spender])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def clean_statement(
    raw_transactions: List[RawTransaction],
    account_name: str,
    spender: str,
) -> List[Transaction]:
    """Normalize raw parsed transactions into cleaned ``Transaction`` objects.

    Amounts are always stored as positive magnitudes representing the size of
    the expense, independent of the CSV's original polarity convention.
    """
    cleaned: List[Transaction] = []
    for raw in raw_transactions:
        amount = abs(Decimal(raw.amount))
        merchant_key = clean_merchant(raw.description)
        transaction_id = make_transaction_id(raw.date, amount, raw.description, account_name, spender)
        cleaned.append(
            Transaction(
                transactionId=transaction_id,
                date=raw.date,
                originalDescription=raw.description,
                merchantKey=merchant_key,
                amount=amount,
                accountName=account_name,
                spender=spender,
            )
        )
    return cleaned
