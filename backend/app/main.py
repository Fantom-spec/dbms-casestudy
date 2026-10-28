"""Expense Tracker REST API (FastAPI + SQLite)."""
import re
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import compare, database as dbm
from .schemas import BudgetIn, Expense, ExpenseIn, ExpensePage, ExpenseUpdate

MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


@asynccontextmanager
async def lifespan(_: FastAPI):
    dbm.init_db()
    yield


app = FastAPI(title="Expense Tracker API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)

BASE = ("SELECT e.expense_id, e.amount, c.name AS category, e.spent_on, e.note, "
        "e.updated_at, e.synced FROM expense e JOIN category c USING(category_id)")


def _cat_id(con, name: str) -> int:
    row = con.execute("SELECT category_id FROM category WHERE name=?", (name,)).fetchone()
    if row is None:
        raise HTTPException(422, f"Unknown category: {name}")
    return row[0]


def _get(con, expense_id: int) -> Expense:
    row = con.execute(BASE + " WHERE e.expense_id=?", (expense_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Expense not found")
    return Expense(**{**dict(row), "synced": bool(row["synced"])})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories(con: sqlite3.Connection = Depends(dbm.get_db)):
    return [r["name"] for r in con.execute("SELECT name FROM category ORDER BY name")]


@app.get("/api/expenses", response_model=ExpensePage)
def list_expenses(
    q: str = "", category: Optional[str] = None,
    month: Optional[str] = Query(None, pattern=MONTH),
    limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0),
    con: sqlite3.Connection = Depends(dbm.get_db),
):
    where, args = ["COALESCE(e.note,'') LIKE ?"], [f"%{q}%"]
    if category:
        where.append("c.name=?"); args.append(category)
    if month:
        where.append("substr(e.spent_on,1,7)=?"); args.append(month)
    w = " WHERE " + " AND ".join(where)
    total = con.execute("SELECT COUNT(*) FROM expense e JOIN category c USING(category_id)" + w, args).fetchone()[0]
    rows = con.execute(BASE + w + " ORDER BY e.spent_on DESC, e.expense_id DESC LIMIT ? OFFSET ?",
                       [*args, limit, offset]).fetchall()
    return {"items": [{**dict(r), "synced": bool(r["synced"])} for r in rows], "total": total}


@app.post("/api/expenses", response_model=Expense, status_code=201)
def create_expense(body: ExpenseIn, con: sqlite3.Connection = Depends(dbm.get_db)):
    cid = _cat_id(con, body.category)
    with con:
        cur = con.execute(
            "INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)",
            (body.amount, cid, body.note, body.spent_on, dbm.now()))
    return _get(con, cur.lastrowid)


@app.get("/api/expenses/{expense_id}", response_model=Expense)
def get_expense(expense_id: int, con: sqlite3.Connection = Depends(dbm.get_db)):
    return _get(con, expense_id)


@app.patch("/api/expenses/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, body: ExpenseUpdate, con: sqlite3.Connection = Depends(dbm.get_db)):
    _get(con, expense_id)
    fields = body.model_dump(exclude_unset=True)
    sets, args = [], []
    if "category" in fields and fields["category"] is not None:
        sets.append("category_id=?"); args.append(_cat_id(con, fields.pop("category")))
    fields.pop("category", None)
    for k, v in fields.items():
        if v is None:
            continue
        sets.append(f"{k}=?"); args.append(v)
    if sets:
        with con:
            con.execute(f"UPDATE expense SET {', '.join(sets)}, updated_at=?, synced=0 WHERE expense_id=?",
                        [*args, dbm.now(), expense_id])
    return _get(con, expense_id)


@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, con: sqlite3.Connection = Depends(dbm.get_db)):
    _get(con, expense_id)
    with con:
        con.execute("DELETE FROM expense WHERE expense_id=?", (expense_id,))


@app.get("/api/summary")
def summary(month: str = Query(..., pattern=MONTH), con: sqlite3.Connection = Depends(dbm.get_db)):
    """Per-category spend vs budget for a month."""
    rows = con.execute(
        "SELECT c.name AS category, ROUND(COALESCE(SUM(e.amount),0),2) AS spent, b.limit_amt AS budget "
        "FROM category c "
        "LEFT JOIN expense e ON e.category_id=c.category_id AND substr(e.spent_on,1,7)=? "
        "LEFT JOIN budget b ON b.category_id=c.category_id AND b.month=? "
        "GROUP BY c.name, b.limit_amt ORDER BY spent DESC", (month, month)).fetchall()
    cats = [{**dict(r), "over_budget": r["budget"] is not None and r["spent"] > r["budget"]} for r in rows]
    return {"month": month, "total": round(sum(c["spent"] for c in cats), 2), "categories": cats}


@app.get("/api/months")
def months(con: sqlite3.Connection = Depends(dbm.get_db)):
    return [r[0] for r in con.execute(
        "SELECT DISTINCT substr(spent_on,1,7) m FROM expense ORDER BY m DESC")]


@app.put("/api/budgets")
def set_budget(body: BudgetIn, con: sqlite3.Connection = Depends(dbm.get_db)):
    cid = _cat_id(con, body.category)
    with con:
        con.execute("INSERT INTO budget(category_id,month,limit_amt) VALUES(?,?,?) "
                    "ON CONFLICT(category_id,month) DO UPDATE SET limit_amt=excluded.limit_amt",
                    (cid, body.month, body.limit_amt))
    return body


@app.get("/api/sync/pending")
def pending(con: sqlite3.Connection = Depends(dbm.get_db)):
    return {"count": con.execute("SELECT COUNT(*) FROM expense WHERE synced=0").fetchone()[0]}


@app.get("/api/compare/status")
def compare_status():
    return compare.pg_status()


@app.post("/api/compare/run")
def compare_run(sizes: str = "1000,10000"):
    """Runs live benchmarks (can take several seconds; 100000 rows takes ~10+ s on PostgreSQL)."""
    try:
        wanted = [int(x) for x in sizes.split(",") if x]
    except ValueError:
        raise HTTPException(422, "sizes must be comma-separated integers")
    return compare.run(wanted)
