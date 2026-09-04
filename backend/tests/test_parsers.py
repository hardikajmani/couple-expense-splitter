import pytest

from app.parsers.registry import parse_statement
from app.parsers.base import UnsupportedCsvError


SCOTIA_CREDIT_CSV = """Date,Description,Sub-description,Amount
01/05/2024,POS PURCHASE WALMART #1234,WINNIPEG MB,-45.23
01/06/2024,AMAZON.CA*ABC123,,-19.99
"""

SCOTIA_HEADERLESS_CSV = """01/05/2024,POS PURCHASE WALMART #1234 WINNIPEG MB,,-45.23
01/06/2024,UBER TRIP HELP.UBER.COM,,-12.50
"""


def test_parse_scotiabank_credit_with_header():
    txns, account_type, bank = parse_statement(SCOTIA_CREDIT_CSV, "scotia_credit_card.csv")
    assert bank == "scotiabank"
    assert account_type == "credit"
    assert len(txns) == 2
    assert txns[0].amount == -45.23 or str(txns[0].amount) == "-45.23"


def test_parse_scotiabank_headerless():
    txns, account_type, bank = parse_statement(SCOTIA_HEADERLESS_CSV, "scotia_chequing.csv")
    assert bank == "scotiabank"
    assert len(txns) == 2


def test_unsupported_csv_raises_clear_error():
    with pytest.raises(UnsupportedCsvError):
        parse_statement("foo,bar,baz\n1,2,3\n", "mystery_bank.csv")
