"""
SQLite database layer for search history and statistics.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from app.config import Config


def _ensure_dirs() -> None:
    """Create instance folder if it does not exist."""
    path = Config.DATABASE_PATH
    parent = path.rsplit("/", 1)[0] if "/" in path else path.rsplit("\\", 1)[0]
    if parent and parent != path:
        import os
        os.makedirs(parent, exist_ok=True)


@contextmanager
def get_db():
    """Context manager yielding a SQLite connection with row factory."""
    _ensure_dirs()
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables on first run."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                total_sites INTEGER NOT NULL,
                found_count INTEGER NOT NULL,
                not_found_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                avg_response_ms REAL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                site_name TEXT NOT NULL,
                url TEXT,
                status TEXT NOT NULL,
                response_time_ms REAL,
                screenshot_path TEXT,
                FOREIGN KEY (search_id) REFERENCES searches(id)
            );

            CREATE INDEX IF NOT EXISTS idx_searches_username ON searches(username);
            CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at);
            """
        )


def save_search(
    username: str,
    results: list[dict[str, Any]],
) -> int:
    """
    Persist a completed search and its per-site results.
    Returns the new search_id.
    """
    found = sum(1 for r in results if r.get("status") == "found")
    not_found = sum(1 for r in results if r.get("status") == "not_found")
    errors = sum(1 for r in results if r.get("status") == "error")
    times = [r["response_time_ms"] for r in results if r.get("response_time_ms")]
    avg_ms = sum(times) / len(times) if times else 0.0

    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO searches
            (username, total_sites, found_count, not_found_count, error_count,
             avg_response_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                len(results),
                found,
                not_found,
                errors,
                round(avg_ms, 2),
                datetime.utcnow().isoformat() + "Z",
            ),
        )
        search_id = cur.lastrowid

        for r in results:
            conn.execute(
                """
                INSERT INTO search_results
                (search_id, site_name, url, status, response_time_ms, screenshot_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    search_id,
                    r.get("site_name", ""),
                    r.get("url"),
                    r.get("status", "error"),
                    r.get("response_time_ms"),
                    r.get("screenshot_path"),
                ),
            )
        return search_id


def get_search_history(limit: int = 20) -> list[dict]:
    """Return recent searches for the history panel."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, username, total_sites, found_count, not_found_count,
                   error_count, avg_response_ms, created_at
            FROM searches
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_search_by_id(search_id: int) -> dict | None:
    """Load a single search with all site results."""
    with get_db() as conn:
        search = conn.execute(
            "SELECT * FROM searches WHERE id = ?",
            (search_id,),
        ).fetchone()
        if not search:
            return None
        results = conn.execute(
            "SELECT * FROM search_results WHERE search_id = ? ORDER BY site_name",
            (search_id,),
        ).fetchall()
    return {
        "search": dict(search),
        "results": [dict(r) for r in results],
    }


def get_dashboard_stats() -> dict:
    """Aggregate stats for dashboard cards."""
    with get_db() as conn:
        total_searches = conn.execute(
            "SELECT COUNT(*) FROM searches"
        ).fetchone()[0]
        total_found = conn.execute(
            "SELECT COALESCE(SUM(found_count), 0) FROM searches"
        ).fetchone()[0]
        unique_usernames = conn.execute(
            "SELECT COUNT(DISTINCT username) FROM searches"
        ).fetchone()[0]
        avg_time = conn.execute(
            "SELECT COALESCE(AVG(avg_response_ms), 0) FROM searches"
        ).fetchone()[0]
    return {
        "total_searches": total_searches,
        "total_profiles_found": total_found,
        "unique_usernames": unique_usernames,
        "avg_response_ms": round(avg_time or 0, 2),
    }
