from sortflow.organizer import get_unique_destination
from sortflow import organizer

def test_get_unique_destination(tmp_path):
    destination = tmp_path / "report.txt"

    result = get_unique_destination(destination)

    assert result == destination

def test_get_unique_destination_when_file_exists(tmp_path):
    destination = tmp_path / "report.txt"

    destination.touch()

    result = get_unique_destination(destination)

    assert result == tmp_path / "report_1.txt"

def test_get_unique_destination_multiple_duplicates(tmp_path):
    destination = tmp_path / "report.txt"

    destination.touch()
    (tmp_path / "report_1.txt").touch()

    result = get_unique_destination(destination)

    assert result == tmp_path / "report_2.txt"

def test_organize_file(tmp_path, monkeypatch):
    fake_downloads = tmp_path / "Downloads"
    fake_documents = tmp_path / "Documents"

    fake_downloads.mkdir()
    fake_documents.mkdir()

    file = fake_downloads / "report.txt"
    file.write_text("Hello")

    monkeypatch.setitem(
        organizer.CATEGORY_DIRS,
        "Documents",
        fake_documents,
    )

    organizer.organize_file(file)

    expected_destination = (
        fake_documents
        / "[AUTOMATED]-moved-files"
        / "txt"
        / "report.txt"
    )

    assert expected_destination.exists()
    assert expected_destination.read_text() == "Hello"
    assert not file.exists()