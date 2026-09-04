from decimal import Decimal

import pytest

from app.calculator import calculate_settlement
from app.models import Transaction, SHARED, PERSON_A, PERSON_B, EXCLUDE


def make_txn(spender, amount, cost_assignee, i=0):
    return Transaction(
        transactionId=f"t{i}",
        date="2024-01-01",
        originalDescription="desc",
        merchantKey="merchant",
        amount=Decimal(amount),
        accountName="acc",
        spender=spender,
        costAssignee=cost_assignee,
    )


def test_even_split_settlement():
    txns = [
        make_txn("A", "100.00", SHARED, 1),
        make_txn("B", "0.00", SHARED, 2),
    ]
    result = calculate_settlement(txns, "A", "B", Decimal("0.5"), Decimal("0.5"))
    assert result["sharedExpenses"] == "100.00"
    assert result["expectedShared"]["A"] == "50.00"
    assert result["expectedShared"]["B"] == "50.00"
    assert result["finalSettlement"]["whoOwesWhom"] == "B owes A"
    assert result["finalSettlement"]["amount"] == "50.00"


def test_uneven_ratio_45_55():
    txns = [make_txn("A", "200.00", SHARED, 1)]
    result = calculate_settlement(txns, "A", "B", Decimal("0.45"), Decimal("0.55"))
    assert result["expectedShared"]["A"] == "90.00"
    assert result["expectedShared"]["B"] == "110.00"
    assert result["finalSettlement"]["whoOwesWhom"] == "B owes A"
    assert result["finalSettlement"]["amount"] == "110.00"


def test_personal_expenses_excluded_from_shared_pool():
    txns = [
        make_txn("A", "100.00", SHARED, 1),
        make_txn("A", "30.00", PERSON_A, 2),
        make_txn("B", "20.00", PERSON_B, 3),
    ]
    result = calculate_settlement(txns, "A", "B", Decimal("0.5"), Decimal("0.5"))
    assert result["sharedExpenses"] == "100.00"
    assert result["personalExpenses"]["A"] == "30.00"
    assert result["personalExpenses"]["B"] == "20.00"
    assert result["totalCoupleSpend"] == "150.00"


def test_excluded_transactions_ignored_entirely():
    txns = [
        make_txn("A", "100.00", SHARED, 1),
        make_txn("A", "999.00", EXCLUDE, 2),
    ]
    result = calculate_settlement(txns, "A", "B", Decimal("0.5"), Decimal("0.5"))
    assert result["sharedExpenses"] == "100.00"
    assert result["totalCoupleSpend"] == "100.00"
    assert result["totalSpentByEach"]["A"] == "100.00"


def test_settled_when_no_delta():
    txns = [
        make_txn("A", "50.00", SHARED, 1),
        make_txn("B", "50.00", SHARED, 2),
    ]
    result = calculate_settlement(txns, "A", "B", Decimal("0.5"), Decimal("0.5"))
    assert result["finalSettlement"]["whoOwesWhom"] == "settled"
    assert result["finalSettlement"]["amount"] == "0.00"


def test_ratio_must_sum_to_one():
    with pytest.raises(ValueError):
        calculate_settlement([], "A", "B", Decimal("0.5"), Decimal("0.6"))
