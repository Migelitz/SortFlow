from sortflow import organizer
from sortflow.classifier import ClassificationResult
from sortflow.organizer import get_unique_destination


def test_get_unique_destination(tmp_path):
    destination = tmp_path / "report.txt"
    result = get_unique_destination(destination)
    assert result == destination


def test_get_unique_destination_when_file_exists(tmp_path):
    destination = tmp_path / "report.txt"
    destination.touch()
    result = get_unique_destination(destination)
    assert result == tmp_path / "report_1.txt"


def test_organize_file(tmp_path, monkeypatch):
    # Set up test directories
    fake_downloads = tmp_path / "Downloads"
    fake_dest_base = tmp_path / "Documents" / "School"
    fake_downloads.mkdir(parents=True)

    file = fake_downloads / "report.txt"
    file.write_text("Hello")

    mock_result = ClassificationResult(
        category_name="school",
        destination_base=fake_dest_base,
        confidence=10,
        reasoning=["Mock reasoning"],
    )
    monkeypatch.setattr(organizer, "classify_file", lambda p: mock_result)

    # Mock database writes so we don't need a real SQLite DB for this test
    monkeypatch.setattr(organizer, "record_file_operation", lambda *args, **kwargs: None)
    monkeypatch.setattr(organizer, "record_classification_feedback", lambda *args, **kwargs: None)

    # Run the function
    organizer.organize_file(file)

    # Verify the file was moved to the expected destination
    expected_destination = fake_dest_base / "[AUTOMATED]-moved-files" / "txt" / "report.txt"
    assert expected_destination.exists()
    assert expected_destination.read_text() == "Hello"
    assert not file.exists()
