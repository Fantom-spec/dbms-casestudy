"""Live SQLite vs PostgreSQL comparison (ported from legacy/benchmark.py and
legacy/compare_sqlite_postgres.py). PostgreSQL is optional: set PG_DSN, e.g.
  PG_DSN="dbname=expenses user=temp password=temp123 host=localhost port=5432"
PostgreSQL work happens only in scratch tables named cmp_* (never your real data).
"""
import os, random, sqlite3, statistics as st, tempfile, threading, time, datetime as dt

PG_DSN = os.environ.get("PG_DSN")
REPEAT = 20
SIZES_ALLOWED = (1_000, 10_000, 100_000)
CATS = ["Food", "Transport", "Books", "Entertainment", "Rent", "Health"]
Q_SUM = ("SELECT c.name, SUM(e.amount) FROM cmp_expense e JOIN cmp_category c USING(category_id) "
         "WHERE e.spent_on >= '2026-10-01' AND e.spent_on < '2026-11-01' GROUP BY c.name")
INS = "INSERT INTO cmp_expense(amount,category_id,note,spent_on,updated_at) VALUES({p},{p},{p},{p},{p})"


def _pg():
    import psycopg2
    return psycopg2


def pg_status() -> dict:
    if not PG_DSN:
        return {"available": False, "reason": "PG_DSN environment variable is not set"}
    try:
        pg = _pg()
    except ImportError:
        return {"available": False, "reason": "psycopg2 not installed (pip install psycopg2-binary)"}
    try:
        c = pg.connect(PG_DSN, connect_timeout=3)
        ver = c.cursor(); ver.execute("SHOW server_version"); v = ver.fetchone()[0]; c.close()
        return {"available": True, "version": v}
    except Exception as e:
        return {"available": False, "reason": str(e).strip().splitlines()[0]}


def _med(fn):
    ts = []
    for _ in range(REPEAT):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return round(st.median(ts), 4)


def _rows(n):
    random.seed(1); start = dt.date(2026, 1, 1)
    return [(round(random.uniform(10, 900), 2), random.randint(1, 6), "x",
             (start + dt.timedelta(days=random.randint(0, 300))).isoformat(), "t") for _ in range(n)]


def sqlite_size(n):
    path = os.path.join(tempfile.mkdtemp(), "cmp.db")
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(
        "CREATE TABLE cmp_category(category_id INTEGER PRIMARY KEY, name TEXT UNIQUE);"
        "CREATE TABLE cmp_expense(expense_id INTEGER PRIMARY KEY, amount REAL, category_id INT, "
        "note TEXT, spent_on TEXT, updated_at TEXT); CREATE INDEX cmp_d ON cmp_expense(spent_on);")
    con.executemany("INSERT INTO cmp_category(name) VALUES(?)", [(c,) for c in CATS])
    rows = _rows(n); sql = INS.format(p="?")
    t = time.perf_counter()
    with con: con.executemany(sql, rows)
    bulk = (time.perf_counter() - t) * 1000

    def one():
        with con: con.execute(sql, (5, 1, "y", "2026-10-05", "t"))
    r = {"rows": n, "bulk_insert_ms": round(bulk, 1), "single_insert_ms": _med(one),
         "monthly_sum_ms": _med(lambda: con.execute(Q_SUM).fetchall()),
         "lookup_by_id_ms": _med(lambda: con.execute("SELECT * FROM cmp_expense WHERE expense_id=?", (n // 2,)).fetchone())}
    con.close()
    return r


def pg_size(n):
    con = _pg().connect(PG_DSN); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS cmp_expense, cmp_category CASCADE")
    cur.execute("CREATE TABLE cmp_category(category_id SERIAL PRIMARY KEY, name TEXT UNIQUE)")
    cur.execute("CREATE TABLE cmp_expense(expense_id SERIAL PRIMARY KEY, amount NUMERIC CHECK(amount>0), "
                "category_id INT REFERENCES cmp_category, note TEXT, spent_on DATE, updated_at TEXT)")
    cur.execute("CREATE INDEX ON cmp_expense(spent_on)")
    for c in CATS: cur.execute("INSERT INTO cmp_category(name) VALUES(%s)", (c,))
    con.commit()
    rows = _rows(n); sql = INS.format(p="%s")
    t = time.perf_counter()
    cur.executemany(sql, rows); con.commit()
    bulk = (time.perf_counter() - t) * 1000

    def one():
        cur.execute(sql, (5, 1, "y", "2026-10-05", "t")); con.commit()
    r = {"rows": n, "bulk_insert_ms": round(bulk, 1), "single_insert_ms": _med(one),
         "monthly_sum_ms": _med(lambda: (cur.execute(Q_SUM), cur.fetchall())),
         "lookup_by_id_ms": _med(lambda: (cur.execute("SELECT * FROM cmp_expense WHERE expense_id=%s", (n // 2,)), cur.fetchone()))}
    cur.execute("DROP TABLE IF EXISTS cmp_expense, cmp_category CASCADE"); con.commit(); con.close()
    return r


def _threads(worker, k=4):
    ts = [threading.Thread(target=worker) for _ in range(k)]
    t = time.perf_counter(); [x.start() for x in ts]; [x.join() for x in ts]
    return round((time.perf_counter() - t) * 1000)


def concurrency(per=200, k=4):
    path = os.path.join(tempfile.mkdtemp(), "cc.db")
    s = sqlite3.connect(path); s.execute("PRAGMA journal_mode=WAL")
    s.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v INT)"); s.commit(); s.close()

    def sw():
        c = sqlite3.connect(path, timeout=30)
        for _ in range(per):
            c.execute("INSERT INTO t(v) VALUES(1)"); c.commit()
        c.close()
    out = {"writers": k, "per_writer": per, "sqlite_ms": _threads(sw, k), "postgres_ms": None}
    if PG_DSN:
        pg = _pg(); c = pg.connect(PG_DSN); cur = c.cursor()
        cur.execute("DROP TABLE IF EXISTS cmp_cc"); cur.execute("CREATE TABLE cmp_cc(id SERIAL PRIMARY KEY, v INT)"); c.commit()

        def pw():
            x = pg.connect(PG_DSN); y = x.cursor()
            for _ in range(per):
                y.execute("INSERT INTO cmp_cc(v) VALUES(1)"); x.commit()
            x.close()
        out["postgres_ms"] = _threads(pw, k)
        cur.execute("DROP TABLE IF EXISTS cmp_cc"); c.commit(); c.close()
    return out


def availability():
    """Server-unavailable test: SQLite needs no server; PG is pointed at a dead port."""
    path = os.path.join(tempfile.mkdtemp(), "av.db")
    s = sqlite3.connect(path); s.execute("CREATE TABLE t(v)"); s.execute("INSERT INTO t VALUES(1)"); s.commit()
    out = {"sqlite": "Works with no server: reads and writes succeed", "postgres": None}
    s.close()
    if PG_DSN:
        try:
            _pg().connect(PG_DSN + " port=5999 connect_timeout=2")
            out["postgres"] = "Connected (unexpected)"
        except Exception as e:
            out["postgres"] = "FAILED: " + str(e).strip().splitlines()[0]
    return out


def run(sizes):
    sizes = [n for n in sizes if n in SIZES_ALLOWED] or [1_000]
    pg = pg_status()
    res = {"postgres": pg, "sizes": sizes,
           "sqlite": [sqlite_size(n) for n in sizes],
           "pg": [pg_size(n) for n in sizes] if pg["available"] else None,
           "concurrency": concurrency(), "availability": availability(),
           "setup": {"sqlite": "0 steps: library built into the app, data lives in one file",
                     "postgres": "Install and start a server, create DB and user, configure access, manage backups and security"}}
    if not pg["available"]:
        res["concurrency"]["postgres_ms"] = None
    return res
