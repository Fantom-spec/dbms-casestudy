"""Shows the effect of the index on spent_on using EXPLAIN QUERY PLAN and timings."""
import os, time, random, statistics as st, datetime as dt
import db

Q = "SELECT SUM(amount) FROM expense WHERE spent_on >= '2026-10-01' AND spent_on < '2026-10-08'"
N = 100_000

path = "idx.db"
if os.path.exists(path): os.remove(path)
con = db.connect(path); db.seed(con, n=0)
random.seed(2); start = dt.date(2026, 1, 1)
rows = [(round(random.uniform(10, 900), 2), random.randint(1, 6), "x",
         (start + dt.timedelta(days=random.randint(0, 300))).isoformat(), "t") for _ in range(N)]
with con:
    con.executemany("INSERT INTO expense(amount,category_id,note,spent_on,updated_at) VALUES(?,?,?,?,?)", rows)

def t():
    ts = []
    for _ in range(30):
        a = time.perf_counter(); con.execute(Q).fetchone(); ts.append((time.perf_counter() - a) * 1000)
    return st.median(ts)

def plan():
    return " | ".join(r[3] for r in con.execute("EXPLAIN QUERY PLAN " + Q))

con.execute("DROP INDEX idx_expense_date")
no_idx, p1 = t(), plan()
con.execute("CREATE INDEX idx_expense_date ON expense(spent_on)")
with_idx, p2 = t(), plan()
print(f"Rows: {N:,}\nQuery: one-week total")
print(f"Without index: {no_idx:.3f} ms   plan: {p1}")
print(f"With index:    {with_idx:.3f} ms   plan: {p2}")
print(f"Speed-up: {no_idx / with_idx:.1f}x")
con.close(); os.remove(path)
for e in ("-wal", "-shm"):
    if os.path.exists(path + e): os.remove(path + e)
