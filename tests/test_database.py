import sqlite3

import pytest

from sortflow.database import connection, repository
from sortflow.database import initialize as database_initializer


@pytest.fixture
def initialized_database(tmp_path, monkeypatch):
    database_dir = tmp_path / "sortflow"
    database_path = database_dir / "database.db"

    monkeypatch.setattr(connection, "DATABASE_DIR", database_dir)
    monkeypatch.setattr(connection, "DATABASE_PATH", database_path)

    database_initializer.initialize_database()
    return database_path


def test_database_connection_creates_directory_and_commits(tmp_path, monkeypatch):
    database_dir = tmp_path / "nested" / "sortflow"
    database_path = database_dir / "database.db"
    monkeypatch.setattr(connection, "DATABASE_DIR", database_dir)
    monkeypatch.setattr(connection, "DATABASE_PATH", database_path)

    with connection.database_connection() as conn:
        conn.execute("CREATE TABLE values_table (value TEXT NOT NULL)")
        conn.execute("INSERT INTO values_table VALUES (?)", ("saved",))

    assert database_dir.is_dir()
    with sqlite3.connect(database_path) as conn:
        assert conn.execute("SELECT value FROM values_table").fetchone() == ("saved",)


def test_database_connection_rolls_back_when_operation_fails(initialized_database):
    with pytest.raises(RuntimeError, match="rollback"):
        with connection.database_connection() as conn:
            conn.execute(
                """
                INSERT INTO file_operations (
                    source_path, destination_path, operation, status,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("source.txt", "destination.txt", "move", "failed", "error", "now"),
            )
            raise RuntimeError("rollback")

    with connection.database_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM file_operations").fetchone()[0] == 0


def test_initialize_database_creates_all_tables_and_is_idempotent(initialized_database):
    database_initializer.initialize_database()

    with connection.database_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {"file_operations", "classification_feedback"} <= tables


def test_record_file_operation_persists_operation(initialized_database):
    repository.record_file_operation(
        source_path="/downloads/report.pdf",
        destination_path="/documents/report.pdf",
        operation="move",
        status="success",
    )

    with connection.database_connection() as conn:
        row = conn.execute(
            """
            SELECT source_path, destination_path, operation, status,
                   error_message, created_at
            FROM file_operations
            """
        ).fetchone()

    assert dict(row) == {
        "source_path": "/downloads/report.pdf",
        "destination_path": "/documents/report.pdf",
        "operation": "move",
        "status": "success",
        "error_message": "",
        "created_at": row["created_at"],
    }
    assert row["created_at"]



def test_record_classification_feedback_persists_prediction_and_correction(initialized_database):
    repository.record_classification_feedback(
        filename="report.pdf",
        file_extension=".pdf",
        predicted_category="Pictures",
        corrected_category="Documents",
        file_size_bytes=1024,
        file_modified_at="2026-10-17T01:00:00+00:00",
    )

    with connection.database_connection() as conn:
        row = conn.execute(
            """
            SELECT filename, file_extension, file_size_bytes, file_modified_at,
                   predicted_category, corrected_category, created_at
            FROM classification_feedback
            """
        ).fetchone()

    assert dict(row) == {
        "filename": "report.pdf",
        "file_extension": ".pdf",
        "file_size_bytes": 1024,
        "file_modified_at": "2026-10-17T01:00:00+00:00",
        "predicted_category": "Pictures",
        "corrected_category": "Documents",
        "created_at": row["created_at"],
    }
    assert row["created_at"]


def test_record_classification_feedback_defaults_categories_to_null(initialized_database):
    repository.record_classification_feedback(
        filename="report.pdf",
        file_extension=".pdf",
        file_size_bytes=1024,
        file_modified_at="2026-10-17T01:00:00+00:00",
    )

    with connection.database_connection() as conn:
        row = conn.execute(
            """
            SELECT predicted_category, corrected_category
            FROM classification_feedback
            """
        ).fetchone()

    assert row["predicted_category"] is None
    assert row["corrected_category"] is None


def test_organize_file_records_rule_based_prediction(initialized_database, tmp_path, monkeypatch):
    from sortflow import organizer

    downloads = tmp_path / "Downloads"
    documents = tmp_path / "Documents"
    downloads.mkdir()
    documents.mkdir()
    source = downloads / "report.txt"
    source.write_text("Hello")
    monkeypatch.setitem(organizer.CATEGORY_DIRS, "Documents", documents)

    organizer.organize_file(source)

    with connection.database_connection() as conn:
        operation = conn.execute(
            "SELECT status FROM file_operations"
        ).fetchone()
        feedback = conn.execute(
            """
            SELECT filename, predicted_category, corrected_category, file_size_bytes
            FROM classification_feedback
            """
        ).fetchone()

    assert operation["status"] == "success"
    assert dict(feedback) == {
        "filename": "report.txt",
        "predicted_category": "Documents",
        "corrected_category": None,
        "file_size_bytes": 5,
    }
