"""Benchmark SQLite (embedded). Optional: also PostgreSQL if --pg DSN is given.
Usage:  python benchmark.py
        python benchmark.py --pg "dbname=expenses user=postgres password=... host=localhost"
"""
import os, sys, time, statistics as st, random, datetime as dt
import db

SIZES = [1_000, 10_000, 100_000]
REPEAT = 20
Q_SUM = ("SELECT c.name, SUM(e.amount) FROM expense e JOIN category c USING(category_id) "
         "WHERE e.spent_on >= '2026-10-01' AND e.spent_on < '2026-11-01' GROUP BY c.name")

def timeit(fn):
    ts = []
    for _ in range(REPEAT):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return st.median(ts)

def sqlite_bench(n):
    path = f"bench_{n}.db"
    if os.path.exists(path): os.remove(path)
    con = db.connect(path)
    db.seed(con, n=0)
    ids = [r[0] for r in con.execute("SELECT category_id FROM category")]
    random.seed(1); start = dt.date(2026, 1, 1)
    rows = [(round(random.uniform(10, 900), 2), random.choice(ids), "x",
             (start + dt.timedelta(days=random.randint(0, 300))).isoformat(), "t") for _ in range(n)]
    t = time.perf_counter()
    with con:
        con.executemany("INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)", rows)
    bulk = (time.perf_counter() - t) * 1000
    def one_insert():
        with con: con.execute("INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(5,1,'y','2026-10-05','t')")
    r = {"rows": n, "bulk_insert_ms": bulk,
         "single_insert_ms": timeit(one_insert),
         "monthly_sum_ms": timeit(lambda: con.execute(Q_SUM).fetchall()),
         "lookup_by_id_ms": timeit(lambda: con.execute("SELECT * FROM expense WHERE expense_id=?", (n // 2,)).fetchone())}
    con.close(); os.remove(path)
    for ext in ("-wal", "-shm"):
        if os.path.exists(path + ext): os.remove(path + ext)
    return r

def pg_bench(dsn, n):
    import psycopg2
    con = psycopg2.connect(dsn); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS expense, category CASCADE")
    cur.execute("CREATE TABLE category(category_id SERIAL PRIMARY KEY, name TEXT UNIQUE)")
    cur.execute("CREATE TABLE expense(expense_id SERIAL PRIMARY KEY, amount NUMERIC CHECK(amount>0), "
                "category_id INT REFERENCES category, note TEXT, spent_on DATE, updated_at TEXT)")
    cur.execute("CREATE INDEX ON expense(spent_on)")
    for c in db.CATEGORIES: cur.execute("INSERT INTO category(name) VALUES(%s)", (c,))
    con.commit()
    random.seed(1); start = dt.date(2026, 1, 1)
    rows = [(round(random.uniform(10, 900), 2), random.randint(1, 6), "x",
             start + dt.timedelta(days=random.randint(0, 300)), "t") for _ in range(n)]
    t = time.perf_counter()
    cur.executemany("INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(%s,%s,%s,%s,%s)", rows)
    con.commit(); bulk = (time.perf_counter() - t) * 1000
    def one_insert():
        cur.execute("INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(5,1,'y','2026-10-05','t')"); con.commit()
    pgsum = Q_SUM.replace("USING(category_id)", "USING(category_id)")
    r = {"rows": n, "bulk_insert_ms": bulk, "single_insert_ms": timeit(one_insert),
         "monthly_sum_ms": timeit(lambda: (cur.execute(pgsum), cur.fetchall())),
         "lookup_by_id_ms": timeit(lambda: (cur.execute("SELECT * FROM expense WHERE expense_id=%s", (n // 2,)), cur.fetchone()))}
    con.close(); return r

def table(title, results):
    print(f"\n{title}  (median of {REPEAT} runs, milliseconds)")
    print(f"{'rows':>9} {'bulk insert':>12} {'1 insert':>10} {'monthly sum':>12} {'lookup id':>10}")
    for r in results:
        print(f"{r['rows']:>9,} {r['bulk_insert_ms']:>12.1f} {r['single_insert_ms']:>10.3f} "
              f"{r['monthly_sum_ms']:>12.3f} {r['lookup_by_id_ms']:>10.4f}")

if __name__ == "__main__":
    table("SQLite (embedded, in-process)", [sqlite_bench(n) for n in SIZES])
    if "--pg" in sys.argv:
        dsn = sys.argv[sys.argv.index("--pg") + 1]
        table("PostgreSQL (client-server, localhost)", [pg_bench(dsn, n) for n in SIZES])
