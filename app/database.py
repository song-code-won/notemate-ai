"""
Database management for NoteMate AI.
Handles SQLite persistent storage, schema migrations, and connection management.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

DEFAULT_DB_PATH = os.path.join("data", "notes.db")


def get_db_path() -> str:
    """Resolve the SQLite database file path from environment or default."""
    db_url = os.getenv("DATABASE_URL", DEFAULT_DB_PATH)
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
    elif db_url.startswith("sqlite://"):
        db_path = db_url.replace("sqlite://", "")
    else:
        db_path = db_url
    
    # Ensure parent directory exists
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    return db_path


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional scope around a series of operations."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency and write resilience
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database tables and indexes."""
    db_path = get_db_path()
    parent = Path(db_path).parent
    parent.mkdir(parents=True, exist_ok=True)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at DESC);
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
            """
        )


def current_iso_time() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()
