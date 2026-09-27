import logging
import time
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread

from watchdog.events import (
    FileCreatedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from sortflow.config import DOWNLOADS_DIR
from sortflow.organizer import organize_file

# Storage for paths of files that need processing
event_queue = Queue()
pending_paths = set()  # This is not thread safe so we use Lock to allow one thread at a time
paths_lock = Lock()
logger = logging.getLogger(__name__)  # ID for logs on who's log is this coming from


class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)

        with paths_lock:
            if path in pending_paths:
                return

            pending_paths.add(path)

        event_queue.put(path)
        logger.info("File detected: %s", path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.dest_path)

        # A file moved out of Downloads is reported as a deletion
        # because the destination is outside the watched directory.

        with paths_lock:
            if path in pending_paths:
                return

            pending_paths.add(path)

        event_queue.put(path)
        logger.info("File moved into Downloads: %s", path)


def is_in_downloads(path: Path) -> bool:
    """Prevents file organize from moving files that went outside of Downloads directory"""
    return path.is_relative_to(DOWNLOADS_DIR)


def wait_for_file(
    path: Path,
    stable_checks: int = 3,
    check_interval: float = 1.0,
) -> bool:
    """Wait until a file's size remains unchanged for several checks."""

    checks = 0
    previous_size = None

    while checks < stable_checks:
        try:
            current_size = path.stat().st_size
        except FileNotFoundError:
            logger.warning("File disappeared while waiting: %s", path)
            return False

        if current_size == previous_size:
            checks += 1
        else:
            checks = 0

        previous_size = current_size
        time.sleep(check_interval)

    return True


def process_files() -> None:
    while True:
        # .get() puts the thread to sleep waiting while the queue is empty
        # Queue class handle putting thread worker to sleep
        path = event_queue.get()

        try:
            # Check again because the file may have moved
            # since the original filesystem event.
            if not is_in_downloads(path):
                logger.info("Skipping file — no longer in Downloads: %s", path)
                continue

            if wait_for_file(path):
                # Check again after waiting because the file
                # could move while waiting.
                if not is_in_downloads(path):
                    logger.info("Skipping file — moved outside Downloads while waiting: %s", path)
                    continue

                organize_file(path)

        finally:
            with paths_lock:
                pending_paths.discard(path)
            event_queue.task_done()


def start_watcher() -> None:
    event_handler = DownloadHandler()

    observer = Observer()
    observer.schedule(event_handler, str(DOWNLOADS_DIR))

    worker = Thread(target=process_files, daemon=True)

    logger.info("Starting file watcher for: %s", DOWNLOADS_DIR)
    worker.start()
    observer.start()
    logger.info("File watcher started successfully")

    shutdown_event = Event()

    try:
        # Sleep the main program and wake when something happen
        shutdown_event.wait()
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
        observer.stop()

    observer.join()
    logger.info("File watcher stopped")