"""Shared data models / constants for the expense splitter backend."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

CATEGORIES = [
    "rent",
    "groceries",
    "food",
    "travel",
    "car",
    "insurance",
    "subscription",
    "utilities",
    "shopping",
    "entertainment",
    "transfer",
    "other",
]

UNREVIEWED_CATEGORY = "other"

ACCOUNT_TYPES = ["credit", "chequing", "savings"]

# costAssignee values
SHARED = 0
PERSON_A = 1
PERSON_B = 2
EXCLUDE = -1

VALID_COST_ASSIGNEES = {SHARED, PERSON_A, PERSON_B, EXCLUDE}


@dataclass
class RawTransaction:
    """A transaction as extracted directly from a bank CSV, before cleaning."""

    date: str
    description: str
    amount: Decimal
    raw_row: dict = field(default_factory=dict)


@dataclass
class Transaction:
    """A normalized, cleaned transaction ready for categorization/review."""

    transactionId: str
    date: str
    originalDescription: str
    merchantKey: str
    amount: Decimal
    accountName: str
    spender: str
    category: str = UNREVIEWED_CATEGORY
    costAssignee: int = SHARED
    reviewed: bool = False

    def to_dict(self) -> dict:
        return {
            "transactionId": self.transactionId,
            "date": self.date,
            "originalDescription": self.originalDescription,
            "merchantKey": self.merchantKey,
            "amount": str(self.amount),
            "accountName": self.accountName,
            "spender": self.spender,
            "category": self.category,
            "costAssignee": self.costAssignee,
            "reviewed": self.reviewed,
        }

    @staticmethod
    def from_dict(data: dict) -> "Transaction":
        return Transaction(
            transactionId=data["transactionId"],
            date=data["date"],
            originalDescription=data["originalDescription"],
            merchantKey=data["merchantKey"],
            amount=Decimal(str(data["amount"])),
            accountName=data["accountName"],
            spender=data["spender"],
            category=data.get("category", UNREVIEWED_CATEGORY),
            costAssignee=int(data.get("costAssignee", SHARED)),
            reviewed=bool(data.get("reviewed", False)),
        )
