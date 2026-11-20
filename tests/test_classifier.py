import pytest

import sortflow.classifier as classifier
from sortflow.classifier import classify_file


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    """Mocks the configuration so tests don't depend on real home directory."""
    test_dest = tmp_path / "TestDest"

    test_categories = {
        "school": {
            "destination": test_dest / "School",
            "extensions": [".pdf"],
            "keywords": {"assignment": 5, "course": 4},
        }
    }

    monkeypatch.setattr("sortflow.classifier.CATEGORIES", test_categories)
    monkeypatch.setattr("sortflow.classifier.MIN_CONFIDENCE_THRESHOLD", 5)
    monkeypatch.setattr("sortflow.classifier.UNCATEGORIZED_DIR", test_dest / "Uncategorized")

    return test_dest


def test_classify_file_by_filename(mock_config, monkeypatch, tmp_path):
    # Mock extractor to return empty string (simulating no content)
    monkeypatch.setattr("sortflow.classifier.extract_text", lambda p: "")

    file_path = tmp_path / "CS101_assignment_final.pdf"
    file_path.write_text("dummy pdf data")

    result = classify_file(file_path)

    assert result.category_name == "school"
    assert result.confidence == 6  # Filename keyword (+5) and extension (+1)
    assert "school" in str(result.destination_base).lower()


def test_classify_file_by_content(mock_config, monkeypatch, tmp_path):
    # Mock extractor to simulate finding keywords inside a generic text file
    monkeypatch.setattr("sortflow.classifier.extract_text", lambda p: "this is for my course.")

    file_path = tmp_path / "unknown_name.txt"
    file_path.write_text("this is for my course.")
    result = classify_file(file_path)

    # 4 points for 'course' is below the threshold of 5, so it should fail safely
    assert result.category_name == "uncategorized"
    assert result.confidence == 4
    assert "uncategorized" in str(result.destination_base).lower()


def test_classify_file_combined_score_passes_threshold(mock_config, monkeypatch, tmp_path):
    # Extension matches (+1), Content matches (+4) = Total 5
    monkeypatch.setattr("sortflow.classifier.extract_text", lambda p: "this is for my course.")

    file_path = tmp_path / "unknown_name.pdf"
    file_path.write_text("dummy data with course keyword")
    result = classify_file(file_path)

    assert result.category_name == "school"
    assert result.confidence >= 5


@pytest.mark.parametrize(
    ("filename", "expected_category"),
    [
        ("CS101_Assignment.pdf", "school"),
        ("Database Systems Final Exam.pdf", "school"),
        ("Professor_Lecture_Notes.docx", "school"),
        ("Job_Offer.pdf", "work"),
        ("Employee_Payslip.pdf", "work"),
        ("Client_Project_Proposal.docx", "work"),
        ("OJT_Documents.pdf", "work"),
        ("PhilSys_ID.pdf", "personal"),
        ("Bank_Statement.pdf", "personal"),
        ("Shopee_Receipt.pdf", "personal"),
        ("Family_Photos.jpg", "personal"),
    ],
)
def test_expanded_vocabulary_classifies_representative_files(
    monkeypatch, tmp_path, filename, expected_category
):
    monkeypatch.setattr(classifier, "extract_text", lambda path: "")

    file_path = tmp_path / filename
    file_path.write_text("")

    result = classify_file(file_path)

    assert result.category_name == expected_category


@pytest.mark.parametrize(
    "filename",
    [
        "Database_Project.pdf",
        "Project_Report.docx",
    ],
)
def test_weak_ambiguous_keywords_remain_uncategorized(monkeypatch, tmp_path, filename):
    monkeypatch.setattr(classifier, "extract_text", lambda path: "")

    file_path = tmp_path / filename
    file_path.write_text("")

    result = classify_file(file_path)

    assert result.category_name == "uncategorized"
