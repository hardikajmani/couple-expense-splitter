"""FastAPI application exposing the expense-splitter pipeline.

Endpoints:
  POST /api/months/{month}/setup           - create/update month setup
  GET  /api/months                         - list months with saved setups
  GET  /api/months/{month}/setup           - fetch month setup
  POST /api/months/{month}/upload          - upload+parse+clean+categorize a CSV
  GET  /api/months/{month}/transactions    - list all cleaned transactions for review
  PUT  /api/months/{month}/transactions/{transaction_id} - edit category/costAssignee
  POST /api/months/{month}/approve         - persist mappings + approved snapshot
  GET  /api/months/{month}/dashboard       - settlement summary for the month
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.calculator import calculate_settlement
from app.categorizer import Categorizer
from app.cleaner import clean_statement
from app.models import CATEGORIES, VALID_COST_ASSIGNEES, Transaction
from app.parsers.base import UnsupportedCsvError
from app.parsers.registry import parse_statement
from app.storage import DuplicateFileError, Storage

app = FastAPI(title="Couple Expense Splitter API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = Storage()


class SetupRequest(BaseModel):
    personA: str
    personB: str
    ratioA: float = 50
    ratioB: float = 50

    @field_validator("personA", "personB")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Person name cannot be blank")
        return v.strip()

    @field_validator("ratioB")
    @classmethod
    def ratio_sums_to_100(cls, v: float, info) -> float:
        ratio_a = info.data.get("ratioA")
        if ratio_a is not None and abs((ratio_a + v) - 100) > 0.001:
            raise ValueError("ratioA + ratioB must equal 100")
        return v


class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    costAssignee: Optional[int] = None

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v is not None and v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v

    @field_validator("costAssignee")
    @classmethod
    def valid_cost_assignee(cls, v):
        if v is not None and v not in VALID_COST_ASSIGNEES:
            raise ValueError("costAssignee must be one of -1, 0, 1, 2")
        return v


class BulkUpdateItem(TransactionUpdate):
    transactionId: str


class BulkUpdateRequest(BaseModel):
    updates: List[BulkUpdateItem]


def _month_ratios(setup: dict) -> tuple[Decimal, Decimal]:
    try:
        ratio_a = Decimal(str(setup["ratioA"])) / Decimal("100")
        ratio_b = Decimal(str(setup["ratioB"])) / Decimal("100")
    except (KeyError, InvalidOperation) as exc:
        raise HTTPException(status_code=500, detail="Invalid stored ratio") from exc
    return ratio_a, ratio_b


def _require_setup(month: str) -> dict:
    setup = storage.load_setup(month)
    if not setup:
        raise HTTPException(status_code=404, detail=f"No setup found for month {month}. Create it first.")
    return setup


@app.post("/api/months/{month}/setup")
def create_setup(month: str, body: SetupRequest):
    setup = body.model_dump()
    storage.save_setup(month, setup)
    return setup


@app.get("/api/months/{month}/setup")
def get_setup(month: str):
    return _require_setup(month)


@app.get("/api/months")
def list_months():
    return storage.list_months()


@app.post("/api/months/{month}/upload")
async def upload_statement(month: str, person: str = Form(...), file: UploadFile = File(...)):
    setup = _require_setup(month)
    if person not in (setup["personA"], setup["personB"]):
        raise HTTPException(status_code=400, detail=f"Unknown person '{person}' for this month's setup")

    content_bytes = await file.read()
    try:
        content_text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text") from exc

    try:
        raw_transactions, account_type, bank_name = parse_statement(content_text, file.filename or "")
    except UnsupportedCsvError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        storage.save_raw_file(month, person, file.filename or "upload.csv", content_bytes)
    except DuplicateFileError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    account_name = f"{bank_name}_{account_type}".strip("_") or "unknown_account"
    cleaned = clean_statement(raw_transactions, account_name=account_name, spender=person)

    categorizer = Categorizer(storage.data_dir)
    for txn in cleaned:
        category, reviewed = categorizer.categorize(txn.merchantKey)
        txn.category = category
        txn.reviewed = reviewed

    storage.save_clean_transactions(month, person, account_name, cleaned)

    return {
        "accountName": account_name,
        "accountType": account_type,
        "bank": bank_name,
        "transactionCount": len(cleaned),
        "transactions": [t.to_dict() for t in cleaned],
    }


@app.get("/api/months/{month}/transactions")
def list_transactions(month: str):
    _require_setup(month)
    return [t.to_dict() for t in storage.load_all_transactions(month)]


@app.put("/api/months/{month}/transactions/{transaction_id}")
def update_transaction(month: str, transaction_id: str, body: TransactionUpdate):
    _require_setup(month)
    all_txns = storage.load_all_transactions(month)
    target = next((t for t in all_txns if t.transactionId == transaction_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if body.category is not None:
        target.category = body.category
    if body.costAssignee is not None:
        target.costAssignee = body.costAssignee
    target.reviewed = True

    storage.save_clean_transactions(month, target.spender, target.accountName, [target])
    return target.to_dict()


@app.put("/api/months/{month}/transactions")
def bulk_update_transactions(month: str, body: BulkUpdateRequest):
    _require_setup(month)
    all_txns = {t.transactionId: t for t in storage.load_all_transactions(month)}
    updated: List[Transaction] = []
    for item in body.updates:
        target = all_txns.get(item.transactionId)
        if not target:
            continue
        if item.category is not None:
            target.category = item.category
        if item.costAssignee is not None:
            target.costAssignee = item.costAssignee
        target.reviewed = True
        updated.append(target)

    by_person_account: dict = {}
    for t in updated:
        by_person_account.setdefault((t.spender, t.accountName), []).append(t)
    for (person, account_name), txns in by_person_account.items():
        storage.save_clean_transactions(month, person, account_name, txns)

    return [t.to_dict() for t in updated]


@app.post("/api/months/{month}/approve")
def approve_month(month: str):
    setup = _require_setup(month)
    all_txns = storage.load_all_transactions(month)

    unreviewed = [t for t in all_txns if not t.reviewed]
    if unreviewed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{len(unreviewed)} transaction(s) still need review before approval. "
                "Every row (including auto-categorized suggestions) must be confirmed."
            ),
        )

    categorizer = Categorizer(storage.data_dir)
    categorizer.learn_many([(t.merchantKey, t.category) for t in all_txns])

    ratio_a, ratio_b = _month_ratios(setup)
    summary = calculate_settlement(all_txns, setup["personA"], setup["personB"], ratio_a, ratio_b)
    storage.save_approved_snapshot(month, all_txns, summary)
    return summary


@app.get("/api/months/{month}/dashboard")
def dashboard(month: str):
    setup = _require_setup(month)
    approved = storage.load_approved_snapshot(month)
    if approved:
        return approved["summary"]

    all_txns = storage.load_all_transactions(month)
    ratio_a, ratio_b = _month_ratios(setup)
    return calculate_settlement(all_txns, setup["personA"], setup["personB"], ratio_a, ratio_b)


@app.get("/api/categories")
def get_categories():
    return CATEGORIES
