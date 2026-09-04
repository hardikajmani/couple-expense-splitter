"""Parser for Scotiabank-exported CSV statements.

Scotiabank's online banking CSV export has no header row and uses the
column order: Date, Description, Sub-description, Amount (optionally split
into separate Debit/Credit style rows depending on export options). Some
exports do include a header ("Date,Description,Amount" or similar); we
support both so the parser degrades gracefully.
"""
from __future__ import annotations

import csv
import io
import re
from decimal import Decimal
from typing import List, Tuple

from app.models import RawTransaction
from app.parsers.base import BaseParser, UnsupportedCsvError, detect_account_type

_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$|^\d{4}-\d{2}-\d{2}$")

_KNOWN_HEADER_TOKENS = {"date", "description", "amount", "sub-description", "type", "status", "balance"}


class ScotiabankParser(BaseParser):
    bank_name = "scotiabank"

    def sniff(self, filename: str, header: List[str]) -> bool:
        first_cell = header[0].strip() if header else ""
        if _DATE_RE.match(first_cell):
            # Headerless export - first row IS a data row.
            return True
        lowered = {h.strip().lower() for h in header}
        return bool(lowered & _KNOWN_HEADER_TOKENS)

    def parse(self, content: str, filename: str) -> Tuple[List[RawTransaction], str]:
        raw_rows = [r for r in csv.reader(io.StringIO(content)) if any(cell.strip() for cell in r)]
        if not raw_rows:
            raise UnsupportedCsvError("CSV file is empty")

        first_cell = raw_rows[0][0].strip() if raw_rows[0] else ""
        if _DATE_RE.match(first_cell):
            # Headerless export - every row (incl. the first) is data, using
            # the canonical Scotiabank column order.
            columns = ["Date", "Description", "Sub-description", "Amount"][: len(raw_rows[0])]
            data_rows = raw_rows
        else:
            columns = [h.strip() for h in raw_rows[0]]
            data_rows = raw_rows[1:]

        header = columns
        all_rows = []
        for row in data_rows:
            if len(row) < len(columns):
                row = row + [""] * (len(columns) - len(row))
            all_rows.append({columns[i]: row[i].strip() for i in range(len(columns))})

        account_type = detect_account_type(filename, header)

        transactions: List[RawTransaction] = []
        for row in all_rows:
            date = row.get("Date", "").strip()
            if not date:
                continue
            description = (row.get("Description", "") + " " + row.get("Sub-description", "")).strip()
            amount = self._extract_amount(row)
            transactions.append(RawTransaction(date=date, description=description, amount=amount, raw_row=row))
        return transactions, account_type

    def _extract_amount(self, row: dict) -> Decimal:
        if "Amount" in row and row["Amount"] not in ("", None):
            return self._to_decimal(row["Amount"])
        debit = row.get("Debit") or row.get("Withdrawal")
        credit = row.get("Credit") or row.get("Deposit")
        if debit:
            return -self._to_decimal(debit)
        if credit:
            return self._to_decimal(credit)
        return Decimal("0")
