"""Non-interactive demo: run `python demo.py` (about 1 minute)."""
import os, sqlite3
import db

def show(title, rows):
    print(f"\n--- {title} ---")
    for r in rows:
        print("  ", dict(r))
    if not rows: print("   (no rows)")

if os.path.exists("demo.db"): os.remove("demo.db")
con = db.connect("demo.db")
db.seed(con, n=150)
print("Database created offline (no network, no server). Rows:",
      con.execute("SELECT COUNT(*) FROM expense").fetchone()[0])

# CRUD
new_id = db.add_expense(con, 250.0, "Food", "2026-10-27", "team lunch")
show("Added expense", db.search(con, "team lunch"))
db.update_expense(con, new_id, amount=275.0)
show("After update", db.search(con, "team lunch"))
db.delete_expense(con, new_id)
show("After delete", db.search(con, "team lunch"))

# Queries
show("Q1 Monthly total per category (Oct 2026)", db.monthly_totals(con, "2026-10"))
show("Q2 Categories over budget (Oct 2026)", db.over_budget(con, "2026-10"))
show("Q3 Search: Books", db.search(con, "", "Books")[:5])
print("\nQ4 Entries waiting to sync:", len(db.pending_sync(con)))

# Integrity: constraints reject bad data
for label, fn in [
    ("negative amount", lambda: db.add_expense(con, -5, "Food", "2026-10-27")),
    ("unknown category", lambda: db.add_expense(con, 10, "Pets", "2026-10-27")),
    ("FK violation (raw SQL)", lambda: con.execute(
        "INSERT INTO expense(amount,category_id,spent_on,updated_at) VALUES(5,999,'2026-10-27','x')")),
]:
    try:
        fn(); print(f"NOT rejected: {label}")
    except (sqlite3.IntegrityError, ValueError) as e:
        print(f"Rejected ({label}): {e}")

# Atomicity: failed transaction rolls back completely
before = con.execute("SELECT COUNT(*) FROM expense").fetchone()[0]
try:
    with con:
        con.execute("INSERT INTO expense(amount,category_id,spent_on,updated_at) VALUES(10,1,'2026-10-27','x')")
        con.execute("INSERT INTO expense(amount,category_id,spent_on,updated_at) VALUES(-1,1,'2026-10-27','x')")
except sqlite3.IntegrityError:
    pass
after = con.execute("SELECT COUNT(*) FROM expense").fetchone()[0]
print(f"\nAtomicity: rows before={before}, after failed transaction={after} (rolled back)")
