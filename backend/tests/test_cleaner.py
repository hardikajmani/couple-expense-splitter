from decimal import Decimal

from app.cleaner import clean_merchant, clean_statement, make_transaction_id
from app.models import RawTransaction


def test_clean_merchant_removes_pos_purchase_and_location():
    assert clean_merchant("POS PURCHASE WALMART #1234 WINNIPEG MB") == "walmart"


def test_clean_merchant_lowercases_and_strips_ids():
    assert clean_merchant("PURCHASE UBER *TRIP 998877 TORONTO ON") == "uber trip"


def test_clean_merchant_falls_back_when_everything_stripped():
    # If cleaning strips everything, fall back to the lowercased original.
    assert clean_merchant("1234567") != ""


def test_clean_statement_amounts_are_always_positive():
    raws = [
        RawTransaction(date="2024-01-05", description="POS PURCHASE WALMART #1 MB", amount=Decimal("-45.23")),
        RawTransaction(date="2024-01-06", description="PAYROLL DEPOSIT", amount=Decimal("2000.00")),
    ]
    cleaned = clean_statement(raws, account_name="Scotia Credit", spender="A")
    assert all(t.amount > 0 for t in cleaned)
    assert cleaned[0].amount == Decimal("45.23")
    assert cleaned[0].merchantKey == "walmart"


def test_transaction_id_is_stable_and_unique():
    id1 = make_transaction_id("2024-01-05", Decimal("45.23"), "WALMART", "Scotia Credit", "A")
    id2 = make_transaction_id("2024-01-05", Decimal("45.23"), "WALMART", "Scotia Credit", "A")
    id3 = make_transaction_id("2024-01-06", Decimal("45.23"), "WALMART", "Scotia Credit", "A")
    assert id1 == id2
    assert id1 != id3
