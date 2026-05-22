"""SQLite-backed shared memory store with version and timestamp management."""

import sqlite3
import time
from contextlib import contextmanager
from typing import Optional

from prototype.config import DB_PATH
from prototype.memory.models import MemoryEntry, MemoryType


class SharedMemoryStore:
    """SQLite shared memory with working and long-term memory tables."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS working_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                timestamp REAL NOT NULL,
                agent_id TEXT NOT NULL DEFAULT '',
                UNIQUE(key)
            );

            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                timestamp REAL NOT NULL,
                agent_id TEXT NOT NULL DEFAULT '',
                UNIQUE(key)
            );

            CREATE TABLE IF NOT EXISTS conflict_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_type TEXT NOT NULL,
                key TEXT NOT NULL,
                agent_a TEXT NOT NULL,
                agent_b TEXT NOT NULL,
                value_a TEXT,
                value_b TEXT,
                resolved_value TEXT,
                strategy TEXT,
                latency_ms REAL DEFAULT 0.0,
                correct INTEGER DEFAULT 0,
                timestamp REAL NOT NULL
            );
        """)
        self._conn.commit()

    @contextmanager
    def _tx(self):
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _table(self, memory_type: MemoryType) -> str:
        return "working_memory" if memory_type == MemoryType.WORKING else "long_term_memory"

    def read(self, key: str, memory_type: MemoryType = MemoryType.WORKING) -> Optional[MemoryEntry]:
        table = self._table(memory_type)
        row = self._conn.execute(
            f"SELECT key, value, version, timestamp, agent_id FROM {table} WHERE key = ?",
            (key,)
        ).fetchone()
        if row is None:
            return None
        return MemoryEntry(
            key=row[0], value=row[1], version=row[2],
            timestamp=row[3], agent_id=row[4], memory_type=memory_type
        )

    def write(self, key: str, value: str, agent_id: str,
              memory_type: MemoryType = MemoryType.WORKING,
              expected_version: Optional[int] = None) -> MemoryEntry:
        table = self._table(memory_type)
        now = time.time()
        existing = self.read(key, memory_type)

        with self._tx():
            if existing is None:
                version = 1
                self._conn.execute(
                    f"INSERT INTO {table} (key, value, version, timestamp, agent_id) VALUES (?, ?, ?, ?, ?)",
                    (key, value, version, now, agent_id)
                )
            else:
                if expected_version is not None and existing.version != expected_version:
                    raise VersionConflictError(key, existing.version, expected_version)
                version = existing.version + 1
                self._conn.execute(
                    f"UPDATE {table} SET value = ?, version = ?, timestamp = ?, agent_id = ? WHERE key = ?",
                    (value, version, now, agent_id, key)
                )

        return MemoryEntry(
            key=key, value=value, version=version,
            timestamp=now, agent_id=agent_id, memory_type=memory_type
        )

    def get_version(self, key: str, memory_type: MemoryType = MemoryType.WORKING) -> int:
        entry = self.read(key, memory_type)
        return entry.version if entry else 0

    def list_keys(self, memory_type: MemoryType = MemoryType.WORKING) -> list:
        table = self._table(memory_type)
        rows = self._conn.execute(f"SELECT key FROM {table}").fetchall()
        return [r[0] for r in rows]

    def log_conflict(self, conflict_type: str, key: str, agent_a: str, agent_b: str,
                     value_a: str, value_b: str, resolved_value: str,
                     strategy: str, latency_ms: float, correct: bool):
        self._conn.execute(
            """INSERT INTO conflict_log (conflict_type, key, agent_a, agent_b,
               value_a, value_b, resolved_value, strategy, latency_ms, correct, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (conflict_type, key, agent_a, agent_b, value_a, value_b,
             resolved_value, strategy, latency_ms, int(correct), time.time())
        )
        self._conn.commit()

    def reset(self):
        self._conn.executescript("""
            DELETE FROM working_memory;
            DELETE FROM long_term_memory;
            DELETE FROM conflict_log;
        """)
        self._conn.commit()

    def close(self):
        self._conn.close()


class VersionConflictError(Exception):
    def __init__(self, key: str, expected: int, actual: int):
        self.key = key
        self.expected = expected
        self.actual = actual
        super().__init__(f"Version conflict on '{key}': expected {expected}, got {actual}")
