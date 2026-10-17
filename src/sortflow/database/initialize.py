import logging

from sortflow.database.connection import (
    DATABASE_PATH,
    database_connection,
)

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    with database_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_operations (
                id INTEGER PRIMARY KEY,
                source_path TEXT NOT NULL,
                destination_path TEXT,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_extension TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                file_modified_at TEXT NOT NULL,
                predicted_category TEXT,
                corrected_category TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
    logger.info("Database initialized at %s", DATABASE_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()
