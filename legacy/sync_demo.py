"""Offline-first sync simulation.
'remote.db' stands in for a cloud database (Firestore / server). Rows with synced=0 are
pushed when 'online'. Conflicts use last-write-wins on updated_at.
"""
import os, sqlite3
import db

REMOTE_SCHEMA = """CREATE TABLE IF NOT EXISTS expense(
  expense_id INTEGER PRIMARY KEY, amount REAL, category TEXT, note TEXT, spent_on TEXT, updated_at TEXT)"""

def push(local, remote):
    pushed = skipped = 0
    for r in local.execute("SELECT e.*, c.name AS cat FROM expense e JOIN category c USING(category_id) WHERE synced=0"):
        cur = remote.execute("SELECT updated_at FROM expense WHERE expense_id=?", (r["expense_id"],)).fetchone()
        if cur is None or cur[0] < r["updated_at"]:           # last write wins
            remote.execute("INSERT OR REPLACE INTO expense VALUES(?,?,?,?,?,?)",
                           (r["expense_id"], r["amount"], r["cat"], r["note"], r["spent_on"], r["updated_at"]))
            pushed += 1
        else:
            skipped += 1                                       # remote copy is newer
        local.execute("UPDATE expense SET synced=1 WHERE expense_id=?", (r["expense_id"],))
    local.commit(); remote.commit()
    return pushed, skipped

for f in ("sync_local.db", "remote.db"):
    if os.path.exists(f): os.remove(f)
local = db.connect("sync_local.db"); db.seed(local, n=20)
remote = sqlite3.connect("remote.db"); remote.execute(REMOTE_SCHEMA)

print("1. OFFLINE: 23 entries stored locally, pending sync =", len(db.pending_sync(local)),
      "| cloud rows =", remote.execute("SELECT COUNT(*) FROM expense").fetchone()[0])
db.add_expense(local, 99.0, "Food", "2026-10-27", "offline snack")
print("2. Still offline: added one more, pending =", len(db.pending_sync(local)))

print("3. ONLINE: pushing ...", end=" ")
p, s = push(local, remote)
print(f"pushed={p}, skipped={s} | pending now = {len(db.pending_sync(local))} | cloud rows =",
      remote.execute("SELECT COUNT(*) FROM expense").fetchone()[0])

# Conflict: the same expense edited on another device (newer) and on this device (older)
eid = local.execute("SELECT expense_id FROM expense LIMIT 1").fetchone()[0]
remote.execute("UPDATE expense SET amount=777, updated_at='2999-01-01T00:00:00' WHERE expense_id=?", (eid,))
remote.commit()
db.update_expense(local, eid, amount=111)
p, s = push(local, remote)
amt = remote.execute("SELECT amount FROM expense WHERE expense_id=?", (eid,)).fetchone()[0]
print(f"4. CONFLICT on expense {eid}: older local edit vs newer remote edit -> pushed={p}, skipped={s}, cloud amount stays {amt}")

for f in ("sync_local.db", "remote.db", "sync_local.db-wal", "sync_local.db-shm"):
    if os.path.exists(f): os.remove(f)
