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


def test_initialize_database_creates_all_tables_and_is_idempotent(initialized_database):
    database_initializer.initialize_database()

    with connection.database_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
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
        row = conn.execute("SELECT * FROM file_operations").fetchone()

    assert row["source_path"] == "/downloads/report.pdf"
    assert row["status"] == "success"


def test_record_classification_feedback_persists_prediction_and_new_columns(initialized_database):
    repository.record_classification_feedback(
        filename="report.pdf",
        file_extension=".pdf",
        predicted_category="school",
        confidence_score=8,
        matched_signals="Filename contains 'report' (+5)",
        corrected_category="work",
        file_size_bytes=1024,
        file_modified_at="2026-10-17T01:00:00+00:00",
    )

    with connection.database_connection() as conn:
        row = conn.execute("SELECT * FROM classification_feedback").fetchone()

    assert row["predicted_category"] == "school"
    assert row["confidence_score"] == 8
    assert row["matched_signals"] == "Filename contains 'report' (+5)"
    assert row["corrected_category"] == "work"
