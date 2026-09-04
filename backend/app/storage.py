"""Filesystem storage for raw uploads and cleaned/approved transaction data.

Layout:
  data/<YYYY-MM>/raw/<person>/<filename>        (originals, never overwritten)
  data/<YYYY-MM>/clean/<person>/<account>.json  (cleaned transactions)
  data/<YYYY-MM>/clean/approved.json            (approved snapshot for the month)
  data/<YYYY-MM>/setup.json                     (month setup: names + ratio)
  data/merchant_tags.json, data/merchant_patterns.json (global, cross-month)
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional

from app.models import Transaction

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DuplicateFileError(ValueError):
    pass


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class Storage:
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---- paths ----
    def month_dir(self, month: str) -> Path:
        return self.data_dir / month

    def raw_dir(self, month: str, person: str) -> Path:
        return self.month_dir(month) / "raw" / _safe_name(person)

    def clean_dir(self, month: str, person: str) -> Path:
        return self.month_dir(month) / "clean" / _safe_name(person)

    def setup_path(self, month: str) -> Path:
        return self.month_dir(month) / "setup.json"

    def approved_path(self, month: str) -> Path:
        return self.month_dir(month) / "clean" / "approved.json"

    # ---- setup ----
    def save_setup(self, month: str, setup: dict) -> None:
        path = self.setup_path(month)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(setup, indent=2, sort_keys=True), encoding="utf-8")

    def load_setup(self, month: str) -> Optional[dict]:
        path = self.setup_path(month)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_months(self) -> List[str]:
        if not self.data_dir.exists():
            return []
        return sorted(
            p.name for p in self.data_dir.iterdir()
            if p.is_dir() and self.setup_path(p.name).exists()
        )

    # ---- raw file storage ----
    def save_raw_file(self, month: str, person: str, filename: str, content: bytes) -> Path:
        """Save an uploaded file, never overwriting; raises on exact duplicate."""
        raw_dir = self.raw_dir(month, person)
        raw_dir.mkdir(parents=True, exist_ok=True)

        new_hash = file_hash(content)
        for existing in raw_dir.glob("*"):
            if existing.is_file() and file_hash(existing.read_bytes()) == new_hash:
                raise DuplicateFileError(f"File '{filename}' duplicates existing upload '{existing.name}'")

        safe = _safe_name(filename)
        target = raw_dir / safe
        counter = 1
        while target.exists():
            stem, dot, ext = safe.rpartition(".")
            target = raw_dir / (f"{stem}_{counter}.{ext}" if dot else f"{safe}_{counter}")
            counter += 1
        target.write_bytes(content)
        return target

    # ---- cleaned transactions ----
    def save_clean_transactions(self, month: str, person: str, account_name: str, transactions: List[Transaction]) -> Path:
        clean_dir = self.clean_dir(month, person)
        clean_dir.mkdir(parents=True, exist_ok=True)
        path = clean_dir / f"{_safe_name(account_name)}.json"
        existing: List[dict] = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        existing_by_id = {t["transactionId"]: t for t in existing}
        for txn in transactions:
            existing_by_id[txn.transactionId] = txn.to_dict()
        merged = list(existing_by_id.values())
        path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_all_transactions(self, month: str) -> List[Transaction]:
        month_dir = self.month_dir(month) / "clean"
        transactions: List[Transaction] = []
        if not month_dir.exists():
            return transactions
        for person_dir in month_dir.iterdir():
            if not person_dir.is_dir():
                continue
            for account_file in person_dir.glob("*.json"):
                data = json.loads(account_file.read_text(encoding="utf-8"))
                transactions.extend(Transaction.from_dict(d) for d in data)
        return transactions

    def save_approved_snapshot(self, month: str, transactions: List[Transaction], summary: dict) -> Path:
        path = self.approved_path(month)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "transactions": [t.to_dict() for t in transactions],
            "summary": summary,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_approved_snapshot(self, month: str) -> Optional[dict]:
        path = self.approved_path(month)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
