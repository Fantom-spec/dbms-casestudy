"""Data-access layer for the offline-first expense manager (SQLite)."""
import sqlite3, random, datetime as dt, pathlib

HERE = pathlib.Path(__file__).parent
CATEGORIES = ["Food", "Transport", "Books", "Entertainment", "Rent", "Health"]

def connect(path="expenses.db"):
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.row_factory = sqlite3.Row
    con.executescript((HERE / "schema.sql").read_text())
    return con

def now():
    return dt.datetime.now().isoformat(timespec="seconds")

def add_expense(con, amount, category, spent_on, note=""):
    with con:  # transaction: commit on success, rollback on error
        cid = con.execute("SELECT category_id FROM category WHERE name=?", (category,)).fetchone()
        if cid is None:
            raise ValueError(f"Unknown category: {category}")
        cur = con.execute(
            "INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)",
            (amount, cid[0], note, spent_on, now()))
        return cur.lastrowid

def update_expense(con, expense_id, amount=None, note=None):
    with con:
        if amount is not None:
            con.execute("UPDATE expense SET amount=?, updated_at=?, synced=0 WHERE expense_id=?",
                        (amount, now(), expense_id))
        if note is not None:
            con.execute("UPDATE expense SET note=?, updated_at=?, synced=0 WHERE expense_id=?",
                        (note, now(), expense_id))

def delete_expense(con, expense_id):
    with con:
        con.execute("DELETE FROM expense WHERE expense_id=?", (expense_id,))

def search(con, text="", category=None):
    sql = ("SELECT e.expense_id, e.spent_on, c.name AS category, e.amount, e.note "
           "FROM expense e JOIN category c USING(category_id) WHERE e.note LIKE ?")
    args = [f"%{text}%"]
    if category:
        sql += " AND c.name=?"; args.append(category)
    return con.execute(sql + " ORDER BY e.spent_on DESC", args).fetchall()

def monthly_totals(con, month):
    return con.execute(
        "SELECT c.name, ROUND(SUM(e.amount),2) AS total FROM expense e "
        "JOIN category c USING(category_id) WHERE strftime('%Y-%m', e.spent_on)=? "
        "GROUP BY c.name ORDER BY total DESC", (month,)).fetchall()

def over_budget(con, month):
    return con.execute(
        "SELECT c.name, ROUND(SUM(e.amount),2) AS spent, b.limit_amt "
        "FROM expense e JOIN category c USING(category_id) "
        "JOIN budget b ON b.category_id=e.category_id AND b.month=strftime('%Y-%m', e.spent_on) "
        "WHERE b.month=? GROUP BY c.name, b.limit_amt HAVING SUM(e.amount) > b.limit_amt",
        (month,)).fetchall()

def pending_sync(con):
    return con.execute("SELECT * FROM expense WHERE synced=0").fetchall()

def seed(con, n=150, seed_val=7):
    """Insert categories, budgets and n random expenses over Aug-Oct 2026."""
    random.seed(seed_val)
    with con:
        for c in CATEGORIES:
            con.execute("INSERT OR IGNORE INTO category(name) VALUES(?)", (c,))
        ids = {r["name"]: r["category_id"] for r in con.execute("SELECT * FROM category")}
        limits = {"Food": 3000, "Transport": 1500, "Books": 1200,
                  "Entertainment": 1000, "Rent": 6000, "Health": 800}
        for m in ("2026-08", "2026-09", "2026-10"):
            for c, l in limits.items():
                con.execute("INSERT OR IGNORE INTO budget VALUES(?,?,?)", (ids[c], m, l))
        start = dt.date(2026, 8, 1)
        rng = {"Food": (40, 350), "Transport": (20, 250), "Books": (150, 700),
               "Entertainment": (100, 600), "Rent": (3000, 6000), "Health": (50, 500)}
        for m in ("2026-08", "2026-09", "2026-10"):   # one rent payment per month
            con.execute(
                "INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)",
                (5500.0, ids["Rent"], "monthly rent", f"{m}-01", now()))
        for _ in range(n):
            c = random.choice([x for x in CATEGORIES if x != "Rent"])
            d = start + dt.timedelta(days=random.randint(0, 87))
            con.execute(
                "INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)",
                (round(random.uniform(*rng[c]), 2), ids[c], f"{c.lower()} item",
                 d.isoformat(), now()))
