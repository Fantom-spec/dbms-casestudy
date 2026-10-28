import os, tempfile
os.environ["EXPENSE_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from fastapi.testclient import TestClient
from app.main import app


def test_flow():
    with TestClient(app) as c:
        assert "Food" in c.get("/api/categories").json()
        r = c.post("/api/expenses", json={"amount": 12.5, "category": "Food", "spent_on": "2026-10-01", "note": "zzz"})
        assert r.status_code == 201
        eid = r.json()["expense_id"]
        assert c.patch(f"/api/expenses/{eid}", json={"amount": 20}).json()["amount"] == 20
        assert c.get("/api/expenses?q=zzz").json()["total"] == 1
        assert c.post("/api/expenses", json={"amount": -1, "category": "Food", "spent_on": "2026-10-01"}).status_code == 422
        assert c.post("/api/expenses", json={"amount": 1, "category": "Pets", "spent_on": "2026-10-01"}).status_code == 422
        assert c.post("/api/expenses", json={"amount": 1, "category": "Food", "spent_on": "2026-13-45"}).status_code == 422
        s = c.get("/api/summary?month=2026-10").json()
        assert s["total"] > 0 and len(s["categories"]) == 6
        assert c.put("/api/budgets", json={"category": "Food", "month": "2026-10", "limit_amt": 1}).status_code == 200
        assert any(x["over_budget"] for x in c.get("/api/summary?month=2026-10").json()["categories"])
        assert c.delete(f"/api/expenses/{eid}").status_code == 204
        assert c.get(f"/api/expenses/{eid}").status_code == 404


def test_compare_sqlite_only():
    with TestClient(app) as c:
        assert c.get("/api/compare/status").status_code == 200
        r = c.post("/api/compare/run?sizes=1000").json()
        assert r["sqlite"][0]["rows"] == 1000 and r["concurrency"]["sqlite_ms"] > 0
        assert r["availability"]["sqlite"]
