# 5-minute demo and viva script

1. (30 s) Problem: expenses are entered in places with no signal; a server-dependent app fails there.
2. (45 s) Open schema.sql: three tables, PRIMARY/FOREIGN KEYs, CHECK(amount>0), indexes, `synced` flag for later cloud sync.
3. (60 s) Turn Wi-Fi off. Run `python demo.py`: DB is created and used with no server.
4. (60 s) Point at output: add/update/delete, Q1 monthly totals, Q2 over-budget, Q3 search, Q4 pending sync.
5. (45 s) Integrity: negative amount, unknown category and bad foreign key are rejected; the failed transaction rolls back (153 -> 153).
6. (45 s) Run `python benchmark.py`; show the table. If PostgreSQL results are available, show them side by side.
7. (45 s, optional) Run `python index_analysis.py` (scan vs index) and `python sync_demo.py` (offline entries pushed later; conflict resolved by last-write-wins).
8. (15 s) Conclusion: embedded DB for local-first personal data; add a cloud DB only for sync/backup.

## Likely viva questions
- Why SQLite and not MySQL? No server, works offline, in-process latency, tiny footprint; data is single-user and small.
- Is SQLite relational? Yes; the comparison is embedded vs client-server architecture, not SQL vs NoSQL.
- How is ACID provided? Journal/WAL; `with con:` commits or rolls back (shown in demo).
- Limitations? Single writer, no built-in sync/auth/backup, dynamic typing, not for large concurrent workloads.
- Why did the index help? EXPLAIN QUERY PLAN shows SCAN without it and SEARCH USING INDEX with it, so only the matching date range is read.
- How would sync work? Rows with synced=0 are pushed to Firestore/server; updated_at resolves conflicts (last write wins).
- What is Room? Android abstraction over SQLite: entities, DAOs, compile-time query checks, reactive queries.
- Why an index on spent_on? Monthly queries filter by date range; the index avoids a full table scan.
