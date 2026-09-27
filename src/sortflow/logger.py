import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".local" / "state" / "sortflow" / "logs"
LOG_FILE = LOG_DIR / "sortflow.log"
_is_configured = False  # Track initialization state
logger = logging.getLogger(__name__)


def create_log_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def setup_logger() -> None:
    global _is_configured

    # If already set up, exit immediately
    if _is_configured:
        logger.warning("Duplicate logger setup detected. Skipping initialization.")
        return

    create_log_directory(LOG_DIR)

    logging.basicConfig(
        level=logging.INFO,
        format="{asctime} | [{levelname}] | {name} ({filename}:{lineno}): {message}",
        style="{",  # use modern curly-bracket syntax for formatting parameters like {asctime}
        handlers=[
            RotatingFileHandler(
                LOG_FILE,
                maxBytes=5 * 1024 * 1024,  # 5 MiB ≈ 5.24 MB
                backupCount=3,
                encoding="utf-8",
            )
        ],
    )

    # Flip the flag so future calls are blocked
    _is_configured = True

    # Confirmation entry
    logger.info("Logging initialized. Writing to: %s", LOG_FILE)
