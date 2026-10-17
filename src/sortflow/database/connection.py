import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

DATABASE_DIR = Path.home() / ".local" / "share" / "sortflow"
DATABASE_PATH = DATABASE_DIR / "database.db"


@contextmanager
def database_connection() -> Generator[sqlite3.Connection, None, None]:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        yield conn

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
