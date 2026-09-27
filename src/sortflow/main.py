import logging

from sortflow.logger import setup_logger
from sortflow.watcher import start_watcher

# ID for logs on who's log is this coming from
logger = logging.getLogger(__name__)


def main() -> None:
    # Set up logs that allow us to replace print with logging method
    setup_logger()
    logger.info("Initializing SortFlow")
    start_watcher()


if __name__ == "__main__":
    main()
