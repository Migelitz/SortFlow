from datetime import UTC, datetime

from sortflow.database.connection import database_connection


def record_file_operation(
    source_path: str,
    destination_path: str,
    operation: str,
    status: str,
    error_message: str = "",
) -> None:
    with database_connection() as conn:
        conn.execute(
            """
            INSERT INTO file_operations (
                source_path,
                destination_path,
                operation,
                status,
                error_message,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source_path,
                destination_path,
                operation,
                status,
                error_message,
                datetime.now(UTC).isoformat(),
            ),
        )


def record_classification_feedback(
    filename: str,
    file_extension: str,
    file_size_bytes: int,
    file_modified_at: str,
    predicted_category: str | None = None,
    corrected_category: str | None = None,
) -> None:
    with database_connection() as conn:
        conn.execute(
            """
            INSERT INTO classification_feedback (
                filename,
                file_extension,
                file_size_bytes,
                file_modified_at,
                predicted_category,
                corrected_category,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                file_extension,
                file_size_bytes,
                file_modified_at,
                predicted_category,
                corrected_category,
                datetime.now(UTC).isoformat(),
            ),
        )
