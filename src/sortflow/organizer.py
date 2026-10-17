import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sortflow.classifier import classify_file
from sortflow.config import (
    DOCUMENTS_DIR,
    MUSIC_DIR,
    PICTURE_DIR,
    VIDEO_DIR,
)
from sortflow.database.repository import record_classification_feedback, record_file_operation

CATEGORY_DIRS = {
    "Documents": DOCUMENTS_DIR,
    "Music": MUSIC_DIR,
    "Pictures": PICTURE_DIR,
    "Videos": VIDEO_DIR,
}

# ID for logs on who's log is this coming from
logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    name: str = ""
    extension: str = ""
    size: int = 0
    modified_at: str = ""


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
    file_type = classify_file(path)
    destination = get_destination(path)

    if destination is None or file_type is None:
        logger.info("Unsupported file extension; skipping: %s", path.name)
        return

    category, _ = file_type
    create_destination_directory(destination)

    destination = get_unique_destination(destination)

    file_stat = path.stat()

    file = FileMetadata(
        name=path.name,
        extension=path.suffix,
        size=file_stat.st_size,
        modified_at=str(file_stat.st_mtime),
    )

    try:
        path.rename(destination)
        logger.info("File moved successfully: %s", destination)
    except OSError as error:
        logger.error("Failed to move %s to %s: %s", path, destination, error)
        record_file_operation(
            source_path=str(path),
            destination_path=str(destination),
            operation="move",
            status="failed",
            error_message=str(error),
        )
        logger.debug("Recorded file operation for %s", path.name)
        return

    record_file_operation(
        source_path=str(path),
        destination_path=str(destination),
        operation="move",
        status="success",
    )
    logger.debug("Recorded file operation for %s", path.name)

    try:
        record_classification_feedback(
            filename=file.name,
            file_extension=file.extension,
            file_size_bytes=file.size,
            file_modified_at=file.modified_at,
            predicted_category=category,
        )
        logger.debug("Recorded classification feedback for %s", path.name)
    except sqlite3.Error as error:
        logger.exception("Failed to record classification feedback for %s: %s", path.name, error)
