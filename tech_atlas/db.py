"""SQLite connection and schema management."""

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "atlas.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    domain      TEXT,
    entry_type  TEXT NOT NULL CHECK (entry_type IN ('category', 'variant', 'topic', 'stub')),
    parent_id   TEXT REFERENCES entries(id),
    data        TEXT NOT NULL  -- JSON; full schema-conforming Entry object
);

CREATE INDEX IF NOT EXISTS idx_entries_parent ON entries(parent_id);
CREATE INDEX IF NOT EXISTS idx_entries_domain ON entries(domain);
CREATE INDEX IF NOT EXISTS idx_entries_name   ON entries(name);
CREATE INDEX IF NOT EXISTS idx_entries_type   ON entries(entry_type);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(CREATE_SQL)
