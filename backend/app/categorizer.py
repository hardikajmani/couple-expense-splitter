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
from app.storage import _atomic_write_json, _lock_for

DEFAULT_CATEGORY_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "category_rules.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _default_category_rules() -> dict:
    repo_rules = _load_json(DEFAULT_CATEGORY_RULES_PATH)
    if repo_rules:
        return repo_rules
    return {"legacy_aliases": {}, "default_patterns": {}}


def _save_json(path: Path, data: dict) -> None:
    with _lock_for(path):
        _atomic_write_json(path, data)


class Categorizer:
    def __init__(self, data_dir: Path):
        self.tags_path = data_dir / "merchant_tags.json"
        self.patterns_path = data_dir / "merchant_patterns.json"
        self.category_rules_path = data_dir / "category_rules.json"

        rules = _load_json(self.category_rules_path)
        if not rules or ("legacy_aliases" not in rules and "default_patterns" not in rules):
            rules = _default_category_rules()
            _save_json(self.category_rules_path, rules)

        default_rules = rules.get("default_patterns") or {}
        legacy_aliases = rules.get("legacy_aliases") or {}

        self.tags: Dict[str, str] = _load_json(self.tags_path)
        self.legacy_category_map = legacy_aliases

        patterns = _load_json(self.patterns_path)
        merged = {**default_rules, **patterns}
        self.patterns: Dict[str, str] = {
            pattern: self.legacy_category_map.get(category, category)
            for pattern, category in sorted(merged.items(), key=lambda item: (-len(item[0]), item[0]))
        }
        if not self.patterns_path.exists():
            _save_json(self.patterns_path, self.patterns)

    def categorize(self, merchant_key: str) -> Tuple[str, bool]:
        """Return (category, reviewed) for a merchant key."""
        key = (merchant_key or "").strip().lower()
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
