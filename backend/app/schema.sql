PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS category (
  category_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS expense (
  expense_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  amount      REAL NOT NULL CHECK (amount > 0),
  category_id INTEGER NOT NULL REFERENCES category(category_id),
  note        TEXT,
  spent_on    TEXT NOT NULL,                 -- ISO date YYYY-MM-DD
  updated_at  TEXT NOT NULL,
  synced      INTEGER NOT NULL DEFAULT 0     -- 0 = pending cloud sync
);

CREATE TABLE IF NOT EXISTS budget (
  category_id INTEGER NOT NULL REFERENCES category(category_id),
  month       TEXT NOT NULL,                 -- YYYY-MM
  limit_amt   REAL NOT NULL CHECK (limit_amt > 0),
  PRIMARY KEY (category_id, month)
);

CREATE INDEX IF NOT EXISTS idx_expense_date ON expense(spent_on);
CREATE INDEX IF NOT EXISTS idx_expense_cat  ON expense(category_id);
