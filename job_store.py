"""
job_store.py — Persistent SQLite-backed job store.

Replaces the in-memory `jobs = {}` dict in api_server.py.
Jobs survive server restarts and are automatically cleaned up after TTL_HOURS.

Usage:
    from job_store import job_store
    job_store.create(job_id, initial_data)
    job_store.update(job_id, patch_dict)
    job_store.get(job_id)          # returns dict or None
    job_store.delete(job_id)
    job_store.cleanup()            # call periodically to remove expired jobs
"""

import sqlite3
import json
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TTL_HOURS = 2          # jobs older than this are auto-deleted
DB_PATH   = "./jobs.db"  # file sits next to api_server.py; add to .gitignore


class JobStore:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        # background cleanup every 10 minutes
        self._start_cleanup_thread()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id      TEXT PRIMARY KEY,
                    status      TEXT NOT NULL DEFAULT 'starting',
                    current_node TEXT NOT NULL DEFAULT 'starting',
                    data        TEXT,          -- JSON blob
                    error       TEXT,
                    start_time  REAL NOT NULL,
                    updated_at  REAL NOT NULL
                )
            """)
            conn.commit()
        logger.info("JobStore initialised at %s", self._db_path)

    def _start_cleanup_thread(self):
        def _loop():
            while True:
                time.sleep(600)   # every 10 min
                try:
                    self.cleanup()
                except Exception as e:
                    logger.warning("JobStore cleanup error: %s", e)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    # ── public API ────────────────────────────────────────────────────────────

    def create(self, job_id: str, initial: dict) -> None:
        """Insert a new job row."""
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO jobs (job_id, status, current_node, data, error, start_time, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    initial.get("status", "starting"),
                    initial.get("current_node", "starting"),
                    json.dumps(initial.get("data")),
                    initial.get("error"),
                    now,
                    now,
                ),
            )
            conn.commit()

    def update(self, job_id: str, patch: dict) -> None:
        """
        Merge patch into the stored job.
        Recognises top-level keys: status, current_node, error, data.
        Any key not recognised is merged into the 'data' JSON blob.
        """
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                logger.warning("JobStore.update: unknown job_id %s", job_id)
                return

            status       = patch.get("status",       row["status"])
            current_node = patch.get("current_node", row["current_node"])
            error        = patch.get("error",        row["error"])

            # merge data blob
            existing_data = json.loads(row["data"]) if row["data"] else {}
            if existing_data is None:
                existing_data = {}
            if "data" in patch and isinstance(patch["data"], dict):
                existing_data.update(patch["data"])

            # any other keys go into data as well
            known_keys = {"status", "current_node", "error", "data",
                          "job_id", "start_time"}
            for k, v in patch.items():
                if k not in known_keys:
                    existing_data[k] = v

            conn.execute(
                """UPDATE jobs
                   SET status=?, current_node=?, error=?, data=?, updated_at=?
                   WHERE job_id=?""",
                (status, current_node, error, json.dumps(existing_data),
                 time.time(), job_id),
            )
            conn.commit()

    def get(self, job_id: str) -> Optional[dict]:
        """Return the full job as a plain dict, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["data"] = json.loads(result["data"]) if result["data"] else {}
        return result

    def exists(self, job_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return row is not None

    def delete(self, job_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            conn.commit()

    def cleanup(self) -> int:
        """Delete jobs older than TTL_HOURS. Returns number of rows removed."""
        cutoff = time.time() - TTL_HOURS * 3600
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM jobs WHERE start_time < ?", (cutoff,)
            )
            conn.commit()
        removed = cur.rowcount
        if removed:
            logger.info("JobStore cleanup: removed %d expired jobs", removed)
        return removed


# module-level singleton — import this everywhere
job_store = JobStore()
