import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sortflow.classifier import classify_file
from sortflow.database.repository import record_classification_feedback, record_file_operation

# ID for logs on who's log is this coming from
logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    name: str = ""
    extension: str = ""
    size: int = 0
    modified_at: str = ""


def create_destination_directory(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)


def get_unique_destination(destination: Path) -> Path:
    """
    Generate a unique destination path to prevent overwriting existing files.

    If the destination already exists, append an incrementing numeric suffix to the filename (e.g., file_1.pdf, file_2.pdf) until an unused path is found.
    """

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

    if target_path != destination:
        logger.info("Collision resolved: renamed to %s", target_path.name)

    return target_path


def organize_file(path: Path) -> None:
    """Organize a file from the Downloads directory."""
    try:
        # Do not follow links into arbitrary locations, move directories, or
        # create telemetry for empty placeholders produced by download tools.
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            logger.info("Skipping symlink, non-file, or empty path: %s", path)
            return
    except OSError as error:
        logger.warning("Cannot inspect path %s: %s", path, error)
        return

    logger.info("Processing: %s", path.name)

    # 1. Classify
    try:
        result = classify_file(path)
    except Exception as error:
        logger.exception("Classification crashed for %s: %s", path.name, error)
        return

    # Log reasoning
    for reason in result.reasoning:
        logger.debug("Score Reason: %s", reason)

    logger.info("Classification: %s (score=%d)", result.category_name, result.confidence)

    # 2. Build Destination (Preserving original subfolder structure)
    extension_folder = path.suffix.lower().lstrip(".") or "unknown"
    final_dest_dir = result.destination_base / "[AUTOMATED]-moved-files" / extension_folder

    try:
        create_destination_directory(final_dest_dir)
    except OSError as error:
        logger.exception("Failed to create directory %s: %s", final_dest_dir, error)
        return

    destination = get_unique_destination(final_dest_dir / path.name)
    logger.info("Destination: %s", destination)

    # 3. Metadata & Move
    try:
        file_stat = path.stat()
        file_meta = FileMetadata(
            name=path.name,
            extension=path.suffix,
            size=file_stat.st_size,
            modified_at=str(file_stat.st_mtime),
        )

        # link() fails with FileExistsError instead of replacing a destination,
        # unlike rename(). This makes the final collision decision atomic.
        # unlink() completes the move, and requires both paths to share a
        # filesystem; an OSError is logged if that assumption is not true.
        while True:
            try:
                os.link(path, destination)
                break
            except FileExistsError:
                # Another process may have claimed the candidate after
                # get_unique_destination() checked it, so choose another name.
                destination = get_unique_destination(final_dest_dir / path.name)

        path.unlink()
        logger.info("Moved successfully.")
    except PermissionError:
        logger.error("Permission denied moving %s to %s", path.name, destination)
        return
    except FileNotFoundError:
        logger.error("File %s disappeared before it could be moved.", path.name)
        return
    except OSError as error:
        logger.exception("OS Error moving %s to %s: %s", path, destination, error)
        record_file_operation(str(path), str(destination), "move", "failed", str(error))
        return

    # 4. Database Logging
    record_file_operation(str(path), str(destination), "move", "success")

    # Combine the reasoning list into a single string for the database
    signals_str = " | ".join(result.reasoning)

    try:
        record_classification_feedback(
            filename=file_meta.name,
            file_extension=file_meta.extension,
            file_size_bytes=file_meta.size,
            file_modified_at=file_meta.modified_at,
            predicted_category=result.category_name,
            confidence_score=result.confidence,
            matched_signals=signals_str,
        )
        logger.debug("Recorded classification feedback for %s", path.name)
    except sqlite3.Error as error:
        logger.exception("Failed to record classification feedback for %s: %s", path.name, error)
