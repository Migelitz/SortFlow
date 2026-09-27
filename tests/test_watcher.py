from sortflow import watcher


def test_is_in_download(monkeypatch, tmp_path):
    fake_downloads = tmp_path / "Downloads"
    fake_downloads.mkdir()

    monkeypatch.setattr(watcher, "DOWNLOADS_DIR", fake_downloads)

    assert watcher.is_in_downloads(fake_downloads / "report.pdf")


def test_is_not_in_downloads(monkeypatch, tmp_path):
    fake_downloads = tmp_path / "Downloads"
    fake_downloads.mkdir()

    # Create a separate folder outside Downloads
    other_folder = tmp_path / "Documents"
    other_folder.mkdir()

    monkeypatch.setattr(watcher, "DOWNLOADS_DIR", fake_downloads)

    # Path points outside Downloads
    outside_file = other_folder / "report.pdf"

    assert watcher.is_in_downloads(outside_file) is False

def test_nested_path_is_in_downloads(monkeypatch, tmp_path):
    fake_downloads = tmp_path / "Downloads"
    fake_downloads.mkdir()

    monkeypatch.setattr(watcher, "DOWNLOADS_DIR", fake_downloads)

    nested_file = fake_downloads / "some_folder" / "report.pdf"

    assert watcher.is_in_downloads(nested_file)

def test_wait_for_file_when_stable(tmp_path):
    file = tmp_path / "report.txt"
    file.write_text("Hello")

    result = watcher.wait_for_file(
        file,
        stable_checks=2,
        check_interval=0.01,
    )

    assert result is True

def test_wait_for_file_when_file_disappears(tmp_path):
    file = tmp_path / "report.txt"

    result = watcher.wait_for_file(
        file,
        stable_checks=2,
        check_interval=0.01,
    )

    assert result is False