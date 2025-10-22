"""Data access object for transcription history."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from .schema import apply_migrations

DEFAULT_RETENTION_DAYS: Final[int] = 90


@dataclass
class Utterance:
    """Represents a stored transcription utterance."""

    id: int
    text: str
    created_utc: int
    duration_ms: Optional[int]
    mode: str
    raw_text: Optional[str]


class HistoryDAO:
    """Database access layer for transcription history."""

    def __init__(
        self, db_path: Path, retention_days: int = DEFAULT_RETENTION_DAYS
    ) -> None:
        self._db_path = db_path
        self._retention_days = retention_days
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        """Open database connection and apply migrations."""
        if self._conn is not None:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        apply_migrations(self._conn)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def insert(
        self,
        text: str,
        mode: str,
        duration_ms: Optional[int] = None,
        raw_text: Optional[str] = None,
    ) -> int:
        """Insert a new utterance and return its ID."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        created_utc = int(time.time())
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO utterances (text, created_utc, duration_ms, mode, raw_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (text, created_utc, duration_ms, mode, raw_text),
        )
        self._conn.commit()
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("Failed to insert utterance")
        return row_id

    def search(self, query: str, limit: int = 50) -> list[Utterance]:
        """Full-text search across utterances."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT u.id, u.text, u.created_utc, u.duration_ms, u.mode, u.raw_text
            FROM utterances_fts fts
            JOIN utterances u ON fts.rowid = u.id
            WHERE utterances_fts MATCH ?
            ORDER BY u.created_utc DESC
            LIMIT ?
            """,
            (query, limit),
        )
        return [self._row_to_utterance(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 50) -> list[Utterance]:
        """Get the most recent utterances."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, text, created_utc, duration_ms, mode, raw_text
            FROM utterances
            ORDER BY created_utc DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_utterance(row) for row in cursor.fetchall()]

    def get_by_id(self, utterance_id: int) -> Optional[Utterance]:
        """Get a specific utterance by ID."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, text, created_utc, duration_ms, mode, raw_text
            FROM utterances
            WHERE id = ?
            """,
            (utterance_id,),
        )
        row = cursor.fetchone()
        return self._row_to_utterance(row) if row else None

    def delete_older_than(self, days: int) -> int:
        """Delete utterances older than the specified number of days."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cutoff = int(time.time()) - (days * 86400)
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM utterances WHERE created_utc < ?", (cutoff,))
        self._conn.commit()
        return cursor.rowcount

    def clear_all(self) -> int:
        """Delete all utterances."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM utterances")
        self._conn.commit()
        return cursor.rowcount

    def count(self) -> int:
        """Return the total number of utterances."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM utterances")
        row = cursor.fetchone()
        return row[0] if row else 0

    def apply_retention_policy(self) -> int:
        """Delete utterances older than retention period."""
        return self.delete_older_than(self._retention_days)

    def export_all_to_dict(self) -> list[dict[str, object]]:
        """Export all utterances as a list of dictionaries."""
        if not self._conn:
            raise RuntimeError("Database not opened")

        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, text, created_utc, duration_ms, mode, raw_text
            FROM utterances
            ORDER BY created_utc DESC
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "text": row["text"],
                "created_utc": row["created_utc"],
                "duration_ms": row["duration_ms"],
                "mode": row["mode"],
                "raw_text": row["raw_text"],
            }
            for row in rows
        ]

    def _row_to_utterance(self, row: sqlite3.Row) -> Utterance:
        return Utterance(
            id=row["id"],
            text=row["text"],
            created_utc=row["created_utc"],
            duration_ms=row["duration_ms"],
            mode=row["mode"],
            raw_text=row["raw_text"],
        )
