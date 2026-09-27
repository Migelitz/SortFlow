from pathlib import Path

EXTENSION_MAP = {
    ".pdf": ("Documents", "pdf"),
    ".docx": ("Documents", "docx"),
    ".csv": ("Documents", "csv"),
    ".xlsx": ("Documents", "xlsx"),
    ".txt": ("Documents", "txt"),
    ".pptx": ("Documents", "pptx"),
    ".png": ("Pictures", "png"),
    ".jpg": ("Pictures", "jpg"),
    ".jpeg": ("Pictures", "jpeg"),
    ".mp3": ("Music", "mp3"),
    ".mp4": ("Videos", "mp4"),
}


def classify_file(path: Path) -> tuple[str, str] | None:
    extension = path.suffix.lower()

    return EXTENSION_MAP.get(extension)
