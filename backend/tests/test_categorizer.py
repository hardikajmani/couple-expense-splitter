import json

from app.categorizer import Categorizer


def test_unknown_merchant_defaults_to_other_unreviewed(tmp_path):
    cat = Categorizer(tmp_path)
    category, reviewed = cat.categorize("some totally unknown biz")
    assert category == "other"
    assert reviewed is False


def test_pattern_match_categorizes_but_not_reviewed(tmp_path):
    cat = Categorizer(tmp_path)
    category, reviewed = cat.categorize("uber trip")
    assert category == "travel"
    assert reviewed is False

    category, reviewed = cat.categorize("amazon.ca")
    assert category == "shopping"

    category, reviewed = cat.categorize("walmart")
    assert category == "groceries"

    category, reviewed = cat.categorize("instacart order")
    assert category == "groceries"


def test_learn_persists_exact_mapping_across_instances(tmp_path):
    cat = Categorizer(tmp_path)
    cat.learn("costco", "groceries")

    cat2 = Categorizer(tmp_path)
    category, reviewed = cat2.categorize("costco")
    assert category == "groceries"
    assert reviewed is True

    data = json.loads((tmp_path / "merchant_tags.json").read_text())
    assert data["costco"] == "groceries"


def test_exact_tag_overrides_pattern(tmp_path):
    cat = Categorizer(tmp_path)
    cat.learn("uber eats", "food")
    category, reviewed = cat.categorize("uber eats")
    assert category == "food"
    assert reviewed is True
