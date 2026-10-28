# Offline-First Expense Manager (SQLite) - BCSE302 L Case Study 1

Requires only Python 3.8+ (sqlite3 is built in). No server, no internet.

    python demo.py        # full scripted demo: CRUD, queries, constraints, rollback
    python app.py         # interactive menu (add/update/delete/search/summary)
    python benchmark.py   # SQLite timings at 1k / 10k / 100k rows
    python index_analysis.py  # EXPLAIN QUERY PLAN and timing with vs without index
    python sync_demo.py   # offline -> cloud sync simulation with conflict handling

Optional comparison with a client-server database (needs PostgreSQL + `pip install psycopg2-binary`):

    python benchmark.py --pg "dbname=expenses user=postgres password=YOURPASS host=localhost"

Create the database first in psql: `CREATE DATABASE expenses;`

Files: schema.sql (tables, constraints, indexes), db.py (data-access layer and queries),
demo.py, app.py, benchmark.py, index_analysis.py, sync_demo.py.
