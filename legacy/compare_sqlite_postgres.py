"""Side-by-side showcase: SQLite (embedded) vs PostgreSQL (client-server).

Setup (once):
  pip install psycopg2-binary
  Start PostgreSQL, e.g. with Docker:
    docker run -d --name pg -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres:16
  then create the database:
    docker exec -it pg psql -U postgres -c "CREATE DATABASE expenses;"

Run:
  python compare_sqlite_postgres.py "dbname=expenses user=postgres password=pw host=localhost port=5432"
Without a DSN, only the SQLite half runs.
"""
import sys, os, time, sqlite3, threading, statistics as st

DSN = sys.argv[1] if len(sys.argv) > 1 else None
N_LOOKUP, N_WRITE, THREADS, PER_THREAD = 1000, 200, 4, 200

def ms(f, n):
    t = time.perf_counter()
    for i in range(n): f(i)
    return (time.perf_counter() - t) * 1000 / n

# ---------- SQLite setup ----------
if os.path.exists("cmp.db"): os.remove("cmp.db")
sl = sqlite3.connect("cmp.db"); sl.execute("PRAGMA journal_mode=WAL")
sl.execute("CREATE TABLE expense(id INTEGER PRIMARY KEY, amount REAL, note TEXT)")
sl.executemany("INSERT INTO expense(amount,note) VALUES(?,?)", [(i, "x") for i in range(10000)]); sl.commit()

# ---------- PostgreSQL setup ----------
pg = None
if DSN:
    import psycopg2
    pg = psycopg2.connect(DSN); cur = pg.cursor()
    cur.execute("DROP TABLE IF EXISTS expense"); cur.execute("CREATE TABLE expense(id SERIAL PRIMARY KEY, amount NUMERIC, note TEXT)")
    cur.executemany("INSERT INTO expense(amount,note) VALUES(%s,%s)", [(i, "x") for i in range(10000)]); pg.commit()

print("=== 1. Per-operation latency (what the user feels on every tap) ===")
s_look = ms(lambda i: sl.execute("SELECT * FROM expense WHERE id=?", (i % 10000 + 1,)).fetchone(), N_LOOKUP)
def s_ins(i): sl.execute("INSERT INTO expense(amount,note) VALUES(1,'y')"); sl.commit()
s_write = ms(s_ins, N_WRITE)
print(f"SQLite     lookup {s_look:.4f} ms | insert+commit {s_write:.3f} ms")
if pg:
    p_look = ms(lambda i: (cur.execute("SELECT * FROM expense WHERE id=%s", (i % 10000 + 1,)), cur.fetchone()), N_LOOKUP)
    def p_ins(i): cur.execute("INSERT INTO expense(amount,note) VALUES(1,'y')"); pg.commit()
    p_write = ms(p_ins, N_WRITE)
    print(f"PostgreSQL lookup {p_look:.4f} ms | insert+commit {p_write:.3f} ms   (lookup is {p_look/s_look:.0f}x slower than SQLite here)")
    print("Note: this is localhost. On a real phone the server is across mobile data, adding tens of ms per call.")

print("\n=== 2. Server unavailable (no signal / server down) ===")
print("SQLite     :", sl.execute("SELECT COUNT(*) FROM expense").fetchone()[0], "rows read fine, writes still work")
if DSN:
    import psycopg2
    bad = DSN.replace("port=5432", "") + " port=5999 connect_timeout=2"
    try:
        psycopg2.connect(bad); print("PostgreSQL : connected (unexpected)")
    except psycopg2.OperationalError as e:
        print("PostgreSQL : FAILED ->", str(e).strip().splitlines()[0])

print("\n=== 3. Concurrent writers (where PostgreSQL is stronger) ===")
def run_threads(worker):
    ts = [threading.Thread(target=worker) for _ in range(THREADS)]
    t = time.perf_counter(); [x.start() for x in ts]; [x.join() for x in ts]
    return (time.perf_counter() - t) * 1000
def sworker():
    c = sqlite3.connect("cmp.db", timeout=30)
    for _ in range(PER_THREAD):
        c.execute("INSERT INTO expense(amount,note) VALUES(2,'t')"); c.commit()
    c.close()
print(f"SQLite     {THREADS} writers x {PER_THREAD}: {run_threads(sworker):.0f} ms (one writer at a time; others wait)")
if DSN:
    import psycopg2
    def pworker():
        c = psycopg2.connect(DSN); k = c.cursor()
        for _ in range(PER_THREAD):
            k.execute("INSERT INTO expense(amount,note) VALUES(2,'t')"); c.commit()
        c.close()
    print(f"PostgreSQL {THREADS} writers x {PER_THREAD}: {run_threads(pworker):.0f} ms (true concurrent sessions)")

print("\n=== 4. Setup and footprint ===")
print("SQLite     : 0 steps (library built into the app), 1 file:", os.path.getsize("cmp.db") // 1024, "KB")
print("PostgreSQL : install/start server, create DB and user, configure access, manage backups and security")

sl.close()
for f in ("cmp.db", "cmp.db-wal", "cmp.db-shm"):
    if os.path.exists(f): os.remove(f)
