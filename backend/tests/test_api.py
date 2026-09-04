import io

import pytest
from fastapi.testclient import TestClient

from app.main import app, storage


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "data_dir", tmp_path)
    yield


@pytest.fixture
def client():
    return TestClient(app)


CSV_CONTENT = (
    "Date,Description,Sub-description,Amount\n"
    "01/05/2024,POS PURCHASE WALMART #1234,WINNIPEG MB,-45.23\n"
    "01/06/2024,UBER TRIP HELP.UBER.COM,,-12.50\n"
)


def test_full_pipeline(client):
    setup_resp = client.post(
        "/api/months/2024-01/setup",
        json={"personA": "Alice", "personB": "Bob", "ratioA": 50, "ratioB": 50},
    )
    assert setup_resp.status_code == 200

    upload_resp = client.post(
        "/api/months/2024-01/upload",
        data={"person": "Alice"},
        files={"file": ("scotia_credit.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    body = upload_resp.json()
    assert body["transactionCount"] == 2
    assert body["transactions"][1]["category"] == "travel"  # uber pattern match

    # Re-uploading the exact same file should be rejected as a duplicate.
    dup_resp = client.post(
        "/api/months/2024-01/upload",
        data={"person": "Alice"},
        files={"file": ("scotia_credit.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
    )
    assert dup_resp.status_code == 409

    txns_resp = client.get("/api/months/2024-01/transactions")
    assert txns_resp.status_code == 200
    txns = txns_resp.json()
    assert len(txns) == 2

    walmart_txn = next(t for t in txns if t["merchantKey"] == "walmart")
    assert walmart_txn["category"] == "groceries"  # matched via merchant_patterns.json
    assert walmart_txn["reviewed"] is False

    uber_txn = next(t for t in txns if t["merchantKey"] == "uber trip help uber com")
    assert uber_txn["category"] == "travel"
    assert uber_txn["reviewed"] is False

    update_resp = client.put(
        f"/api/months/2024-01/transactions/{walmart_txn['transactionId']}",
        json={"category": "groceries", "costAssignee": 0},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["category"] == "groceries"

    # Pattern-matched suggestions are guesses and still block approval until
    # explicitly confirmed, even though their category isn't "other".
    blocked_resp = client.post("/api/months/2024-01/approve")
    assert blocked_resp.status_code == 422

    # Confirming without changing category/costAssignee still counts as review.
    confirm_resp = client.put(
        "/api/months/2024-01/transactions",
        json={"updates": [{"transactionId": uber_txn["transactionId"]}]},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()[0]["reviewed"] is True

    approve_resp = client.post("/api/months/2024-01/approve")
    assert approve_resp.status_code == 200
    summary = approve_resp.json()
    assert "finalSettlement" in summary

    dashboard_resp = client.get("/api/months/2024-01/dashboard")
    assert dashboard_resp.status_code == 200
    assert dashboard_resp.json() == summary


def test_approve_blocks_unreviewed_other_category(client):
    client.post(
        "/api/months/2024-02/setup",
        json={"personA": "Alice", "personB": "Bob", "ratioA": 50, "ratioB": 50},
    )
    unknown_csv = (
        "Date,Description,Sub-description,Amount\n"
        "01/05/2024,SOME UNKNOWN BIZ XYZ,,-45.23\n"
    )
    client.post(
        "/api/months/2024-02/upload",
        data={"person": "Alice"},
        files={"file": ("scotia_credit.csv", io.BytesIO(unknown_csv.encode()), "text/csv")},
    )
    resp = client.post("/api/months/2024-02/approve")
    assert resp.status_code == 422


def test_approve_blocks_unconfirmed_pattern_matched_category(client):
    """Pattern-matched categories (e.g. uber -> travel) are guesses and must
    still be explicitly confirmed before approval, even though they aren't
    categorized as 'other'."""
    client.post(
        "/api/months/2024-06/setup",
        json={"personA": "Alice", "personB": "Bob", "ratioA": 50, "ratioB": 50},
    )
    csv_content = (
        "Date,Description,Sub-description,Amount\n"
        "01/05/2024,UBER TRIP HELP.UBER.COM,,-12.50\n"
    )
    upload_resp = client.post(
        "/api/months/2024-06/upload",
        data={"person": "Alice"},
        files={"file": ("scotia_credit.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    txn = upload_resp.json()["transactions"][0]
    assert txn["category"] == "travel"
    assert txn["reviewed"] is False

    resp = client.post("/api/months/2024-06/approve")
    assert resp.status_code == 422

    client.put(
        "/api/months/2024-06/transactions",
        json={"updates": [{"transactionId": txn["transactionId"]}]},
    )
    resp = client.post("/api/months/2024-06/approve")
    assert resp.status_code == 200


def test_invalid_csv_returns_422(client):
    client.post(
        "/api/months/2024-03/setup",
        json={"personA": "Alice", "personB": "Bob", "ratioA": 50, "ratioB": 50},
    )
    resp = client.post(
        "/api/months/2024-03/upload",
        data={"person": "Alice"},
        files={"file": ("mystery.csv", io.BytesIO(b"a,b,c\n1,2,3\n"), "text/csv")},
    )
    assert resp.status_code == 422


def test_setup_requires_ratio_sum_to_100(client):
    resp = client.post(
        "/api/months/2024-04/setup",
        json={"personA": "Alice", "personB": "Bob", "ratioA": 45, "ratioB": 45},
    )
    assert resp.status_code == 422
