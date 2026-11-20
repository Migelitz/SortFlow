import re
from dataclasses import dataclass
from pathlib import Path

from sortflow.config import CATEGORIES, MIN_CONFIDENCE_THRESHOLD, UNCATEGORIZED_DIR
from sortflow.extractor import extract_text


@dataclass
class ClassificationResult:
    category_name: str
    destination_base: Path
    confidence: int
    reasoning: list[str]


def normalize_text(text: str) -> str:
    """Replaces punctuation with spaces for clean word boundary matching."""
    return re.sub(r"[_\W]", " ", text).lower()


def classify_file(path: Path) -> ClassificationResult:
    filename_clean = normalize_text(path.stem)
    extension = path.suffix.lower()

    # Extract content (safely bails out if binary/unsupported)
    content_clean = normalize_text(extract_text(path))

    best_category = "uncategorized"
    best_score = 0
    best_reasoning = ["No strong signals found."]
    best_dest = UNCATEGORIZED_DIR

    # Begin scoring the file
    for cat_name, cat_data in CATEGORIES.items():
        score = 0
        reasons = []

        # 1. Extension Boost (Weak signal, but helpful tie-breaker)
        if extension in cat_data["extensions"]:
            score += 1
            reasons.append(f"Extension '{extension}' matches category (+1)")

        # 2. Keyword scoring
        for word, weight in cat_data["keywords"].items():
            # Use regex boundaries to match exact words, not substrings
            pattern = rf"\b{re.escape(word)}\b"

            if re.search(pattern, filename_clean):
                score += weight
                reasons.append(f"Filename contains '{word}' (+{weight})")

            if content_clean and re.search(pattern, content_clean):
                score += weight
                reasons.append(f"Content contains '{word}' (+{weight})")

        # Check if other file extension got better score
        if score > best_score:
            best_score = score
            best_category = cat_name
            best_reasoning = reasons
            best_dest = cat_data["destination"]

    if best_score < MIN_CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            category_name="uncategorized",
            destination_base=UNCATEGORIZED_DIR,
            confidence=best_score,
            reasoning=["Failed to meet minimum confidence threshold. " + ", ".join(best_reasoning)],
        )

    return ClassificationResult(
        category_name=best_category,
        destination_base=best_dest,
        confidence=best_score,
        reasoning=best_reasoning,
    )
