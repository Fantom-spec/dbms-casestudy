"""SQLite connection handling and seed data."""
import os, pathlib, random, sqlite3, datetime as dt
from contextlib import contextmanager

HERE = pathlib.Path(__file__).parent
DB_PATH = os.environ.get("EXPENSE_DB", str(HERE.parent / "expenses.db"))
CATEGORIES = ["Food", "Transport", "Books", "Entertainment", "Rent", "Health"]


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def connect(path: str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript((HERE / "schema.sql").read_text())
    return con


def get_db():
    """FastAPI dependency: one connection per request."""
    con = connect()
    try:
        yield con
    finally:
        con.close()


def seed(con: sqlite3.Connection, n: int = 150, seed_val: int = 7) -> None:
    random.seed(seed_val)
    with con:
        for c in CATEGORIES:
            con.execute("INSERT OR IGNORE INTO category(name) VALUES(?)", (c,))
        ids = {r["name"]: r["category_id"] for r in con.execute("SELECT * FROM category")}
        limits = {"Food": 3000, "Transport": 1500, "Books": 1200,
                  "Entertainment": 1000, "Rent": 6000, "Health": 800}
        months = ("2026-08", "2026-09", "2026-10")
        for m in months:
            for c, l in limits.items():
                con.execute("INSERT OR IGNORE INTO budget VALUES(?,?,?)", (ids[c], m, l))
        rng = {"Food": (40, 350), "Transport": (20, 250), "Books": (150, 700),
               "Entertainment": (100, 600), "Health": (50, 500)}
        ins = "INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)"
        for m in months:
            con.execute(ins, (5500.0, ids["Rent"], "monthly rent", f"{m}-01", now()))
        start = dt.date(2026, 8, 1)
        for _ in range(n):
            c = random.choice(list(rng))
            d = start + dt.timedelta(days=random.randint(0, 87))
            con.execute(ins, (round(random.uniform(*rng[c]), 2), ids[c],
                              f"{c.lower()} item", d.isoformat(), now()))


def init_db() -> None:
    con = connect()
    try:
        if con.execute("SELECT COUNT(*) FROM category").fetchone()[0] == 0:
            seed(con)
    finally:
        con.close()
