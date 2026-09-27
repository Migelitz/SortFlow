import logging
from pathlib import Path

from sortflow.classifier import classify_file
from sortflow.config import (
    DOCUMENTS_DIR,
    MUSIC_DIR,
    PICTURE_DIR,
    VIDEO_DIR,
)

CATEGORY_DIRS = {
    "Documents": DOCUMENTS_DIR,
    "Music": MUSIC_DIR,
    "Pictures": PICTURE_DIR,
    "Videos": VIDEO_DIR,
}

# ID for logs on who's log is this coming from
logger = logging.getLogger(__name__)


def get_destination(path: Path) -> Path | None:
    file_type = classify_file(path)

    if file_type is None:
        return None

    category, extension = file_type

    base_dir = CATEGORY_DIRS[category]
    logger.info("File classified as %s; destination category: %s", extension, category)

    return base_dir / "[AUTOMATED]-moved-files" / extension / path.name


def create_destination_directory(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)


def get_unique_destination(destination: Path) -> Path:
    filename = destination.stem
    suffix = destination.suffix

    target_path = destination
    counter = 1

    while target_path.exists():
        target_path = destination.parent / f"{filename}_{counter}{suffix}"
        logger.info(
            "Destination already exists: %s; trying: %s",
            destination.name,
            target_path.name,
        )
        counter += 1

    return target_path


def organize_file(path: Path) -> None:
    """Organize a file from the Downloads directory."""
    destination = get_destination(path)

    if destination is None:
        logger.info("Unsupported file extension; skipping: %s", path.name)
        return

    create_destination_directory(destination)

    destination = get_unique_destination(destination)

    try:
        path.rename(destination)
        logger.info("File moved successfully: %s", destination)
    except OSError as error:
        logger.error("Failed to move %s to %s: %s", path, destination, error)
