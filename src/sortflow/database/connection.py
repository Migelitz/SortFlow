import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

DATABASE_DIR = Path.home() / ".local" / "share" / "sortflow"
DATABASE_PATH = DATABASE_DIR / "database.db"


@contextmanager
def database_connection() -> Generator[sqlite3.Connection, None, None]:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    # Each operation gets its own connection, so SQLite's thread-affinity
    # default remains safe while independent writers can still contend briefly.
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)

    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Match the connection timeout at SQLite level so concurrent writers
        # wait instead of failing immediately with "database is locked".
        conn.execute("PRAGMA busy_timeout = 10000")

        yield conn

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
