from pathlib import Path

import pytest

from sortflow.classifier import classify_file


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("report.pdf", ("Documents", "pdf")),
        ("report.PDF", ("Documents", "pdf")),
        ("song.mp3", ("Music", "mp3")),
        ("image.png", ("Pictures", "png")),
        ("video.mp4", ("Videos", "mp4")),
        ("unknown.xyz", None),
    ],
)
def test_classify_file(filename, expected):
    result = classify_file(Path(filename))

    assert result == expected
