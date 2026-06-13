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
import os
import tempfile
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TTL_HOURS = 2          # jobs older than this are auto-deleted

DATABASE_URL = os.getenv("DATABASE_URL")

if os.getenv("VERCEL"):
    DB_PATH = os.getenv("JOB_STORE_DB_PATH", os.path.join(tempfile.gettempdir(), "jobs.db"))
else:
    DB_PATH = os.getenv("JOB_STORE_DB_PATH", "./jobs.db")


class JobStore:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._use_postgres = bool(DATABASE_URL)
        self._init_db()
        # background cleanup every 10 minutes
        self._start_cleanup_thread()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _connect(self):
        if self._use_postgres:
            import pg8000
            import urllib.parse
            import ssl

            url = urllib.parse.urlparse(DATABASE_URL)
            database = url.path[1:]
            port = url.port or 5432

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            conn = pg8000.connect(
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=port,
                database=database,
                ssl_context=ssl_context
            )
            return conn
        else:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn

    def _run_query(self, sql: str, params: tuple = (), fetch_one=False, fetch_all=False, commit=False):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if self._use_postgres:
                sql = sql.replace("?", "%s")
            cursor.execute(sql, params)

            result = None
            if fetch_one:
                row = cursor.fetchone()
                if row:
                    if self._use_postgres:
                        colnames = [desc[0] for desc in cursor.description]
                        result = dict(zip(colnames, row))
                    else:
                        result = dict(row)
            elif fetch_all:
                rows = cursor.fetchall()
                if self._use_postgres:
                    colnames = [desc[0] for desc in cursor.description]
                    result = [dict(zip(colnames, r)) for r in rows]
                else:
                    result = [dict(r) for r in rows]

            if commit:
                conn.commit()

            rowcount = cursor.rowcount

            cursor.close()
            if fetch_one or fetch_all:
                return result
            return rowcount
        except Exception as e:
            if commit:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error("JobStore database error: %s", e)
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _init_db(self):
        self._run_query("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id      TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'starting',
                current_node TEXT NOT NULL DEFAULT 'starting',
                data        TEXT,          -- JSON blob
                error       TEXT,
                start_time  REAL NOT NULL,
                updated_at  REAL NOT NULL
            )
        """, commit=True)
        self._run_query("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                job_id      TEXT PRIMARY KEY,
                platform    TEXT NOT NULL,
                post_time   TEXT NOT NULL,
                note        TEXT,
                title       TEXT,
                status      TEXT NOT NULL DEFAULT 'pending'
            )
        """, commit=True)
        logger.info("JobStore initialised (use_postgres=%s)", self._use_postgres)

    def _start_cleanup_thread(self):
        if os.getenv("VERCEL"):
            return

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
        sql = """INSERT INTO jobs (job_id, status, current_node, data, error, start_time, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?)"""
        self._run_query(
            sql,
            (
                job_id,
                initial.get("status", "starting"),
                initial.get("current_node", "starting"),
                json.dumps(initial.get("data")),
                initial.get("error"),
                now,
                now,
            ),
            commit=True
        )

    def update(self, job_id: str, patch: dict) -> None:
        """
        Merge patch into the stored job.
        """
        with self._lock:
            row = self._run_query("SELECT * FROM jobs WHERE job_id = ?", (job_id,), fetch_one=True)
            if row is None:
                logger.warning("JobStore.update: unknown job_id %s", job_id)
                return

            status       = patch.get("status",       row["status"])
            current_node = patch.get("current_node", row["current_node"])
            error        = patch.get("error",        row["error"])

            existing_data = json.loads(row["data"]) if row["data"] else {}
            if existing_data is None:
                existing_data = {}
            if "data" in patch and isinstance(patch["data"], dict):
                existing_data.update(patch["data"])

            known_keys = {"status", "current_node", "error", "data",
                          "job_id", "start_time"}
            for k, v in patch.items():
                if k not in known_keys:
                    existing_data[k] = v

            sql = """UPDATE jobs
                     SET status=?, current_node=?, error=?, data=?, updated_at=?
                     WHERE job_id=?"""
            self._run_query(
                sql,
                (status, current_node, error, json.dumps(existing_data),
                 time.time(), job_id),
                commit=True
            )

    def get(self, job_id: str) -> Optional[dict]:
        """Return the full job as a plain dict, or None if not found."""
        row = self._run_query("SELECT * FROM jobs WHERE job_id = ?", (job_id,), fetch_one=True)
        if row is None:
            return None
        row["data"] = json.loads(row["data"]) if row["data"] else {}
        return row

    def exists(self, job_id: str) -> bool:
        row = self._run_query("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,), fetch_one=True)
        return row is not None

    def delete(self, job_id: str) -> None:
        self._run_query("DELETE FROM jobs WHERE job_id = ?", (job_id,), commit=True)

    def cleanup(self) -> int:
        """Delete jobs older than TTL_HOURS. Returns number of rows removed."""
        cutoff = time.time() - TTL_HOURS * 3600
        removed = self._run_query("DELETE FROM jobs WHERE start_time < ?", (cutoff,), commit=True)
        if removed:
            logger.info("JobStore cleanup: removed %d expired jobs", removed)
        return removed or 0

    def add_scheduled_post(self, job_id: str, platform: str, post_time: str, note: str, title: str, status: str = "pending") -> None:
        """Add a post to the scheduled_posts table."""
        sql = """INSERT INTO scheduled_posts (job_id, platform, post_time, note, title, status)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        self._run_query(sql, (job_id, platform, post_time, note, title, status), commit=True)

    def update_scheduled_post_status(self, job_id: str, platform: str, status: str) -> None:
        """Update the status of a scheduled post."""
        sql = "UPDATE scheduled_posts SET status=? WHERE job_id=? AND platform=?"
        self._run_query(sql, (status, job_id, platform), commit=True)

    def get_scheduled_posts(self) -> list:
        """Return all scheduled posts."""
        return self._run_query("SELECT * FROM scheduled_posts", fetch_all=True) or []


# module-level singleton — import this everywhere
job_store = JobStore()
