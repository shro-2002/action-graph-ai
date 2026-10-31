"""SQLite persistence: meetings, utterances, items (decisions/actions), reminders, events."""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, date TEXT NOT NULL,
  raw_transcript TEXT NOT NULL, extractor TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS utterances (
  id INTEGER PRIMARY KEY, meeting_id INTEGER NOT NULL REFERENCES meetings(id),
  idx INTEGER NOT NULL, speaker TEXT NOT NULL, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY, meeting_id INTEGER NOT NULL REFERENCES meetings(id),
  kind TEXT NOT NULL CHECK (kind IN ('decision','action')),
  text TEXT NOT NULL, owner TEXT, deadline TEXT, subject TEXT, value TEXT,
  speaker TEXT, source_quote TEXT, confidence REAL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','posted','done','superseded')),
  conflict_with INTEGER REFERENCES items(id), conflict_reason TEXT, conflict_score REAL,
  tracker_url TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL REFERENCES items(id),
  message TEXT NOT NULL, created_at TEXT NOT NULL, posted_url TEXT,
  stage TEXT NOT NULL DEFAULT 'due_soon',
  UNIQUE(item_id)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_meeting ON items(meeting_id);
"""

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | None = None) -> sqlite3.Connection:
    """(Re)open the database. Tests pass ':memory:'."""
    global _conn
    path = path or os.getenv("DB_PATH", "data/actiongraph.db")
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(SCHEMA)
    if "stage" not in {r[1] for r in _conn.execute("PRAGMA table_info(reminders)")}:  # databases created before escalation
        _conn.execute("ALTER TABLE reminders ADD COLUMN stage TEXT NOT NULL DEFAULT 'due_soon'")
    return _conn


@contextmanager
def tx():
    if _conn is None:
        connect()
    with _lock, _conn:
        yield _conn


def rows(sql: str, params: tuple = ()) -> list[dict]:
    with tx() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql: str, params: tuple = ()) -> dict | None:
    found = rows(sql, params)
    return found[0] if found else None


def execute(sql: str, params: tuple = ()) -> int:
    with tx() as c:
        return c.execute(sql, params).lastrowid


def log_event(kind: str, payload: dict) -> None:
    execute("INSERT INTO events (ts, kind, payload) VALUES (?,?,?)", (now_iso(), kind, json.dumps(payload)))
