import sys

import pytest

import sortflow.extractor as extractor
from sortflow.extractor import extract_text


@pytest.mark.parametrize(
    ("extension", "loader_name"),
    [
        (".txt", "_extract_plain_text"),
        (".pdf", "_extract_page_text"),
        (".docx", "_extract_docx_text"),
        (".pptx", "_extract_pptx_text"),
    ],
)
def test_extract_text_uses_only_loader_for_file_type(tmp_path, monkeypatch, extension, loader_name):
    file = tmp_path / f"report{extension}"
    file.write_text("test content")
    calls = []

    for candidate in (
        "_extract_plain_text",
        "_extract_page_text",
        "_extract_docx_text",
        "_extract_pptx_text",
    ):

        def spy(path, candidate=candidate):
            calls.append((candidate, path))
            return "extracted content"

        monkeypatch.setattr(extractor, candidate, spy)

    assert extract_text(file) == "extracted content"
    assert calls == [(loader_name, file)]


def test_lazy_imports_prevent_memory_bloat(tmp_path):
    # Force unload the modules if pytest happened to load them earlier
    sys.modules.pop("pymupdf", None)
    sys.modules.pop("docx", None)
    sys.modules.pop("pptx", None)

    # Create a lightweight text file
    file = tmp_path / "report.txt"
    file.write_text("just some plain text")

    # Extract text
    result = extract_text(file)

    # Prove that the heavy libraries were never loaded into RAM
    assert result == "just some plain text"
    assert "pymupdf" not in sys.modules, "PyMuPDF was loaded unnecessarily!"
    assert "docx" not in sys.modules, "python-docx was loaded unnecessarily!"
    assert "pptx" not in sys.modules, "python-pptx was loaded unnecessarily!"
