from decimal import Decimal

import pytest

from app.storage import Storage, DuplicateFileError
from app.models import Transaction


def test_save_raw_file_never_overwrites_and_detects_duplicates(tmp_path):
    storage = Storage(tmp_path)
    storage.save_raw_file("2024-01", "A", "statement.csv", b"row1,row2")

    # Same content, different name -> duplicate detected.
    with pytest.raises(DuplicateFileError):
        storage.save_raw_file("2024-01", "A", "statement_copy.csv", b"row1,row2")

    # Different content, same name -> not overwritten, saved alongside.
    path2 = storage.save_raw_file("2024-01", "A", "statement.csv", b"different,content")
    assert path2.name != "statement.csv"
    files = list(storage.raw_dir("2024-01", "A").glob("*"))
    assert len(files) == 2


def test_save_and_load_clean_transactions_dedupe_by_id(tmp_path):
    storage = Storage(tmp_path)
    txn = Transaction(
        transactionId="abc123",
        date="2024-01-01",
        originalDescription="desc",
        merchantKey="merchant",
        amount=Decimal("10.00"),
        accountName="Scotia Credit",
        spender="A",
    )
    storage.save_clean_transactions("2024-01", "A", "Scotia Credit", [txn])
    # Re-saving the same transactionId should not create a duplicate entry.
    storage.save_clean_transactions("2024-01", "A", "Scotia Credit", [txn])

    all_txns = storage.load_all_transactions("2024-01")
    assert len(all_txns) == 1
    assert all_txns[0].transactionId == "abc123"


def test_setup_round_trip(tmp_path):
    storage = Storage(tmp_path)
    setup = {"personA": "Alice", "personB": "Bob", "ratioA": "0.5", "ratioB": "0.5"}
    storage.save_setup("2024-01", setup)
    assert storage.load_setup("2024-01") == setup
    assert "2024-01" in storage.list_months()
