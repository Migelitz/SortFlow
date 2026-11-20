import logging
import signal
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

# The watchdog thread only enqueues paths; the worker performs slow stability
# checks, extraction, classification, and moves so event handling stays fast.
event_queue = Queue()
# pending_paths coalesces duplicate events for the same path. Both sets are
# protected because watchdog callbacks and the worker access them concurrently.
pending_paths = set()
# An event arriving while a path is pending must not be discarded: it may
# represent a replacement file or a later write that needs another stability check.
dirty_paths = set()
paths_lock = Lock()
logger = logging.getLogger(__name__)  # ID for logs on who's log is this coming from


class DownloadHandler(FileSystemEventHandler):
    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)

        if is_ignored_file(path):
            return

        with paths_lock:
            if path in pending_paths:
                dirty_paths.add(path)
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
        if is_ignored_file(path):
            return

        with paths_lock:
            if path in pending_paths:
                dirty_paths.add(path)
                return

            pending_paths.add(path)

        event_queue.put(path)
        logger.info("File moved into Downloads: %s", path)


def is_ignored_file(path: Path) -> bool:
    """Ignore hidden system files and browser temporary download files."""
    # Ignore hidden files (e.g., .org.chromium.Chromium.*)
    if path.name.startswith("."):
        return True

    # Ignore active download extensions from Chrome, Firefox, Safari, etc.
    ignored_extensions = {".crdownload", ".part", ".tmp", ".download"}
    if path.suffix.lower() in ignored_extensions:
        return True

    return False


def is_in_downloads(path: Path) -> bool:
    """Prevents file organize from moving files that went outside of Downloads directory"""
    return path.is_relative_to(DOWNLOADS_DIR)


def wait_for_file(
    path: Path,
    stable_checks: int = 3,
    check_interval: float = 1.0,
    max_wait: float = 60.0,
) -> bool:
    """Wait until a file's size and modification time remain unchanged.

    A size-only check can mistake an in-place rewrite for a completed download.
    The deadline prevents one continuously changing file from blocking the
    single worker forever.
    """

    checks = 0
    previous_signature = None
    deadline = time.monotonic() + max_wait

    while checks < stable_checks and time.monotonic() < deadline:
        try:
            file_stat = path.stat()
            current_signature = (file_stat.st_size, file_stat.st_mtime_ns)
        except FileNotFoundError:
            logger.warning("File disappeared while waiting: %s", path)
            return False

        if current_signature == previous_signature:
            checks += 1
        else:
            checks = 0

        previous_signature = current_signature
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(check_interval, remaining))

    if checks < stable_checks:
        logger.warning("File did not stabilize before timeout: %s", path)
        return False

    return True


def process_files() -> None:
    while True:
        # .get() puts the thread to sleep waiting while the queue is empty
        # Queue class handle putting thread worker to sleep
        path = event_queue.get()

        try:
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
                        logger.info(
                            "Skipping file — moved outside Downloads while waiting: %s",
                            path,
                        )
                        continue

                    organize_file(path)
            except Exception:
                # One malformed file, unavailable dependency, or transient
                # filesystem/database error must not kill the daemon's worker.
                logger.exception("Unexpected error processing %s", path)

        finally:
            with paths_lock:
                pending_paths.discard(path)
                should_requeue = path in dirty_paths
                if should_requeue:
                    # Re-add before putting on the queue so a new event cannot
                    # race in and enqueue the same path a second time.
                    dirty_paths.discard(path)
                    pending_paths.add(path)

            if should_requeue:
                event_queue.put(path)
            # Always balance Queue.get(), including when processing raised.
            event_queue.task_done()


def start_watcher() -> None:
    event_handler = DownloadHandler()

    observer = Observer()
    observer.schedule(event_handler, str(DOWNLOADS_DIR))

    worker = Thread(target=process_files, daemon=True)
    shutdown_event = Event()

    def request_shutdown(signum, frame) -> None:
        # SIGTERM is what systemd sends during a normal stop. Signal handlers
        # run in the main thread, so setting an Event safely wakes its wait().
        logger.info("Shutdown requested (signal %s)", signum)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    logger.info("Starting file watcher for: %s", DOWNLOADS_DIR)
    worker.start()
    observer.start()
    logger.info("File watcher started successfully")

    try:
        # Sleep the main program and wake when something happen
        shutdown_event.wait()
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        observer.stop()
        observer.join()
    logger.info("File watcher stopped")
