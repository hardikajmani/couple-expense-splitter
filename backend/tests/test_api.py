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

    update_resp = client.put(
        f"/api/months/2024-01/transactions/{walmart_txn['transactionId']}",
        json={"category": "groceries", "costAssignee": 0},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["category"] == "groceries"

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
