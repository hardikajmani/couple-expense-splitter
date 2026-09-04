"""Merchant categorization backed by persistent JSON mapping files.

- ``merchant_tags.json``: exact merchantKey -> category mapping, learned from
  user review decisions so future months auto-categorize known merchants.
- ``merchant_patterns.json``: substring pattern -> category rules used as a
  fallback for merchants that have not been explicitly reviewed yet
  (e.g. "uber" -> "travel", "amazon" -> "shopping").

Unknown merchants are categorized as ``other`` and marked unreviewed; we
never silently guess a "real" category for something we don't recognize.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from app.models import UNREVIEWED_CATEGORY

DEFAULT_PATTERNS: Dict[str, str] = {
    "uber": "travel",
    "lyft": "travel",
    "amazon": "shopping",
    "walmart": "groceries",
    "instacart": "groceries",
}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


class Categorizer:
    def __init__(self, data_dir: Path):
        self.tags_path = data_dir / "merchant_tags.json"
        self.patterns_path = data_dir / "merchant_patterns.json"
        self.tags: Dict[str, str] = _load_json(self.tags_path)
        patterns = _load_json(self.patterns_path)
        self.patterns: Dict[str, str] = {**DEFAULT_PATTERNS, **patterns}
        if not self.patterns_path.exists():
            _save_json(self.patterns_path, self.patterns)

    def categorize(self, merchant_key: str) -> Tuple[str, bool]:
        """Return (category, reviewed) for a merchant key."""
        key = merchant_key.strip().lower()
        if key in self.tags:
            return self.tags[key], True
        for pattern, category in self.patterns.items():
            if pattern in key:
                return category, False
        return UNREVIEWED_CATEGORY, False

    def learn(self, merchant_key: str, category: str) -> None:
        """Persist a reviewed merchant -> category mapping for future months."""
        key = merchant_key.strip().lower()
        self.tags[key] = category
        _save_json(self.tags_path, self.tags)

    def learn_many(self, mappings: List[Tuple[str, str]]) -> None:
        for merchant_key, category in mappings:
            key = merchant_key.strip().lower()
            self.tags[key] = category
        _save_json(self.tags_path, self.tags)
