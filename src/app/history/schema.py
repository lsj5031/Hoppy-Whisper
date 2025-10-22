"""Database schema and migrations for transcription history."""

from __future__ import annotations

import sqlite3
from typing import Final

SCHEMA_VERSION: Final[int] = 1

CREATE_UTTERANCES_TABLE: Final[str] = """
CREATE TABLE IF NOT EXISTS utterances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_utc INTEGER NOT NULL,
    duration_ms INTEGER,
    mode TEXT NOT NULL,
    raw_text TEXT
);
"""

CREATE_FTS_TABLE: Final[str] = """
CREATE VIRTUAL TABLE IF NOT EXISTS utterances_fts USING fts5(
    text,
    content=utterances,
    content_rowid=id
);
"""

CREATE_FTS_TRIGGERS: Final[str] = """
CREATE TRIGGER IF NOT EXISTS utterances_ai AFTER INSERT ON utterances BEGIN
    INSERT INTO utterances_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS utterances_ad AFTER DELETE ON utterances BEGIN
    DELETE FROM utterances_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS utterances_au AFTER UPDATE ON utterances BEGIN
    UPDATE utterances_fts SET text = new.text WHERE rowid = old.id;
END;
"""

CREATE_METADATA_TABLE: Final[str] = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_INDICES: Final[str] = """
CREATE INDEX IF NOT EXISTS idx_utterances_created ON utterances(created_utc DESC);
CREATE INDEX IF NOT EXISTS idx_utterances_mode ON utterances(mode);
"""


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply database schema and migrations."""
    cursor = conn.cursor()

    cursor.execute(CREATE_METADATA_TABLE)
    cursor.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
    row = cursor.fetchone()
    current_version = int(row[0]) if row else 0

    if current_version < 1:
        cursor.execute(CREATE_UTTERANCES_TABLE)
        cursor.execute(CREATE_FTS_TABLE)
        cursor.executescript(CREATE_FTS_TRIGGERS)
        cursor.executescript(CREATE_INDICES)
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
