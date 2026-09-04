# couple-expense-splitter

A couple expense splitter: two people upload monthly bank/card CSV statements, the app
auto-categorizes transactions, lets you review/edit them, and calculates who owes whom.

- **Backend** (`backend/`): Python + FastAPI. Modular pipeline: `parsers/` (bank-specific
  CSV parsing, currently Scotiabank, extensible to other banks), `cleaner.py` (normalizes
  transactions, cleans merchant names, generates stable transaction IDs), `categorizer.py`
  (persistent `merchant_tags.json` exact mapping + `merchant_patterns.json` substring rules),
  `calculator.py` (Decimal-based settlement math), `storage.py` (raw/clean file persistence
  under `data/<YYYY-MM>/...`).
- **Frontend** (`frontend/`): Next.js app for month setup, per-person statement upload,
  a tabbed review table (bulk edit category/assignee), and a dashboard with the final
  settlement and category pie charts.

## Running locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run tests with `pytest` from the `backend/` directory.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at the backend API
npm run dev
```

