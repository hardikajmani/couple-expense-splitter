"""Settlement calculations using Decimal for money-safe arithmetic.

Ratios apply only to transactions with ``costAssignee == SHARED``; excluded
(-1) transactions are ignored entirely; personal (1/2) transactions count
toward each person's personal spend but not the shared pool.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, List

from app.models import Transaction, SHARED, PERSON_A, PERSON_B, EXCLUDE

TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_settlement(
    transactions: Iterable[Transaction],
    person_a: str,
    person_b: str,
    ratio_a: Decimal,
    ratio_b: Decimal,
) -> dict:
    """Compute the couple's monthly settlement summary.

    ``ratio_a``/``ratio_b`` are fractions (e.g. Decimal("0.5")) that must sum
    to 1. Only ``costAssignee == 0`` (shared) transactions are split by ratio.
    """
    if ratio_a + ratio_b != Decimal("1"):
        raise ValueError("splitRatio must sum to 1")

    shared_expenses = Decimal("0")
    a_personal = Decimal("0")
    b_personal = Decimal("0")
    a_actual_shared_paid = Decimal("0")
    b_actual_shared_paid = Decimal("0")
    total_spent_by_a = Decimal("0")
    total_spent_by_b = Decimal("0")

    for txn in transactions:
        if txn.costAssignee == EXCLUDE:
            continue
        amount = Decimal(txn.amount)
        is_a = txn.spender == person_a
        is_b = txn.spender == person_b

        if txn.costAssignee == SHARED:
            shared_expenses += amount
            if is_a:
                a_actual_shared_paid += amount
            elif is_b:
                b_actual_shared_paid += amount
        elif txn.costAssignee == PERSON_A:
            a_personal += amount
        elif txn.costAssignee == PERSON_B:
            b_personal += amount

        if is_a:
            total_spent_by_a += amount
        elif is_b:
            total_spent_by_b += amount

    total_couple_spend = shared_expenses + a_personal + b_personal
    a_expected_shared = _q(shared_expenses * ratio_a)
    b_expected_shared = shared_expenses - a_expected_shared  # avoid rounding drift

    # Positive delta means this person paid more than their expected share of
    # the shared pool, i.e. the other person owes them.
    a_delta = _q(a_actual_shared_paid - a_expected_shared)
    b_delta = _q(b_actual_shared_paid - b_expected_shared)

    if a_delta > b_delta:
        who_owes_whom = f"{person_b} owes {person_a}"
        amount_owed = _q(a_delta)
    elif b_delta > a_delta:
        who_owes_whom = f"{person_a} owes {person_b}"
        amount_owed = _q(b_delta)
    else:
        who_owes_whom = "settled"
        amount_owed = Decimal("0.00")

    return {
        "sharedExpenses": str(_q(shared_expenses)),
        "personalExpenses": {
            person_a: str(_q(a_personal)),
            person_b: str(_q(b_personal)),
        },
        "totalCoupleSpend": str(_q(total_couple_spend)),
        "totalSpentByEach": {
            person_a: str(_q(total_spent_by_a)),
            person_b: str(_q(total_spent_by_b)),
        },
        "expectedShared": {
            person_a: str(a_expected_shared),
            person_b: str(b_expected_shared),
        },
        "actualSharedPaid": {
            person_a: str(_q(a_actual_shared_paid)),
            person_b: str(_q(b_actual_shared_paid)),
        },
        "finalSettlement": {
            "whoOwesWhom": who_owes_whom,
            "amount": str(amount_owed),
        },
    }
