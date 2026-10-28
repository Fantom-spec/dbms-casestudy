# Expense Tracker (offline-first, SQLite) with SQLite vs PostgreSQL comparison

    backend/   FastAPI + SQLite REST API (+ live benchmark endpoints)
    frontend/  React + Vite UI
    legacy/    original CLI scripts, ER diagram, demo script

## Run

    # terminal 1: API on :8000
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload

    # terminal 2: UI on :5173 (proxies /api to :8000)
    cd frontend
    npm install
    npm run dev

Open http://localhost:5173. The database `backend/expenses.db` is created and seeded on first start.

## SQLite vs PostgreSQL tab

Works with SQLite only out of the box. To enable the PostgreSQL side, create a database and point the backend at it:

    sudo -u postgres psql -c "CREATE DATABASE expenses OWNER temp;"
    export PG_DSN="dbname=expenses user=temp password=temp123 host=localhost port=5432"
    uvicorn app.main:app --reload

Benchmarks only create and drop scratch tables named `cmp_*`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET/POST | /api/expenses | list (q, category, month, limit, offset) / create |
| GET/PATCH/DELETE | /api/expenses/{id} | read / update / delete |
| GET | /api/summary?month=YYYY-MM | spend vs budget per category |
| PUT | /api/budgets | set a category budget for a month |
| GET | /api/categories, /api/months, /api/sync/pending | lookups |
| GET | /api/compare/status | is PostgreSQL reachable |
| POST | /api/compare/run?sizes=1000,10000 | run live benchmarks |

Interactive docs at http://localhost:8000/docs. Tests: `cd backend && pytest`.
