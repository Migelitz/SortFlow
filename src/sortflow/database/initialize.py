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
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                file_extension TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes >= 0),
                file_modified_at TEXT NOT NULL,
                predicted_category TEXT,
                confidence_score INTEGER,
                matched_signals TEXT,
                corrected_category TEXT,
                created_at TEXT NOT NULL,
                label_status TEXT NOT NULL DEFAULT 'unreviewed'
                    CHECK (label_status IN ('unreviewed', 'confirmed', 'corrected', 'rejected')),
                classifier_version TEXT NOT NULL DEFAULT 'rule_based_v1',
                file_hash TEXT,
                reviewed_at TEXT
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS file_operations (
                id INTEGER PRIMARY KEY,
                source_path TEXT NOT NULL,
                destination_path TEXT,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                classification_id INTEGER REFERENCES classification_feedback(id) ON DELETE SET NULL
            );
            """
        )

        # For faster query but the tradeoff is disk space
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_label_status
                ON classification_feedback(label_status)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_operations_classification_id
                ON file_operations(classification_id)
            """
        )
    logger.info("Database initialized at %s", DATABASE_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    initialize_database()
