# SortFlow

A lightweight Python automation tool that automatically organizes files added to my `~/Downloads` directory.

I built this project because my Downloads folder was becoming difficult to manage. Instead of manually moving files into their expected folders, the organizer watches Downloads in the background and automatically sorts supported files into categorized directories.

The project is also part of my Python automation portfolio, with an emphasis on filesystem automation, event-driven programming, testing, logging, and Linux service integration.

## Demo



## Features

* Automatically monitors `~/Downloads`
* Detects newly created or moved files using Watchdog
* Processes files in a background worker thread
* Waits for files to become stable before moving them
* Classifies files by extension
* Moves supported files instead of copying them
* Preserves the original filename
* Automatically handles duplicate filenames
* Ignores unsupported file extensions
* Does not recursively monitor Downloads subdirectories
* Avoids processing files that have moved outside Downloads
* Uses Python's `logging` module for application logging
* Uses rotating log files to prevent unlimited log growth
* Runs headlessly as a `systemd --user` service
* Starts automatically with the user's Linux session

## Supported File Types

The current V1 implementation supports:

| Category  | Extensions                                        |
| --------- | ------------------------------------------------- |
| Documents | `.pdf`, `.docx`, `.csv`, `.xlsx`, `.txt`, `.pptx` |
| Pictures  | `.png`, `.jpg`, `.jpeg`                           |
| Music     | `.mp3`                                            |
| Videos    | `.mp4`                                            |

Unsupported extensions are ignored and remain in `~/Downloads`.

The supported extension list can be expanded as needed.

## How It Organizes Files

Files are placed into an `[AUTOMATED]-moved-files` directory under the appropriate category.

For example:

```text
~/Downloads/report.pdf
        ↓
~/Documents/[AUTOMATED]-moved-files/pdf/report.pdf
```

A picture:

```text
~/Downloads/photo.jpg
        ↓
~/Pictures/[AUTOMATED]-moved-files/jpg/photo.jpg
```

A music file:

```text
~/Downloads/song.mp3
        ↓
~/Music/[AUTOMATED]-moved-files/mp3/song.mp3
```

A video:

```text
~/Downloads/video.mp4
        ↓
~/Videos/[AUTOMATED]-moved-files/mp4/video.mp4
```

### Destination Structure

The resulting directory structure looks like:

```text
~/Documents/
└── [AUTOMATED]-moved-files/
    ├── pdf/
    ├── docx/
    ├── csv/
    ├── xlsx/
    ├── txt/
    └── pptx/

~/Pictures/
└── [AUTOMATED]-moved-files/
    ├── png/
    ├── jpg/
    └── jpeg/

~/Music/
└── [AUTOMATED]-moved-files/
    └── mp3/

~/Videos/
└── [AUTOMATED]-moved-files/
    └── mp4/
```

## Duplicate Files

The organizer does not overwrite an existing file.

If the destination already contains:

```text
report.txt
```

the next file will become:

```text
report_1.txt
```

and subsequent duplicates become:

```text
report_2.txt
report_3.txt
...
```

This prevents existing files from being overwritten during automated organization.

## How It Works

The application follows an event-driven workflow:

```text
                 ~/Downloads
                      │
                      ▼
              Watchdog Observer
                      │
                      ▼
              DownloadHandler
                      │
              filesystem event
                      ▼
                 Event Queue
                      │
                      ▼
               Worker Thread
                      │
                      ▼
              Stability Check
                      │
                      ▼
              File Classification
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
         Documents Pictures Music/Videos
             │        │        │
             └────────┼────────┘
                      ▼
                 Move File
                      │
                      ▼
                    Log
```

### Why Watchdog?

Watchdog provides filesystem event monitoring, allowing the application to react when files are created or moved into Downloads instead of repeatedly scanning the directory.

This makes the application suitable for a lightweight, long-running background process.

### Why a Queue and Worker Thread?

The Watchdog event handler places detected paths into a `Queue`.

The worker thread then processes those paths separately.

Conceptually:

```text
Watchdog event
      ↓
   Queue
      ↓
Worker Thread
      ↓
Process file
```

This keeps filesystem event handling separate from potentially slower operations such as waiting for file stability and moving files.

Python's `Queue` also provides thread-safe communication between the event-handling side and the worker.

### Why Wait for File Stability?

A filesystem event can occur while a file is still being written.

For example, a large download might appear in Downloads before its contents are completely written.

The organizer therefore waits until the file size remains unchanged for several consecutive checks before processing it.

The current implementation uses:

* 3 stable checks
* 1 second between checks

This means the default stability requirement is based on the file size remaining unchanged across consecutive observations.

## Project Structure

```text
sortflow/
├── pyproject.toml
├── README.md
├── TEST_RESULTS.md
├── src/
│   └── sortflow/
│       ├── __init__.py
│       ├── classifier.py
│       ├── config.py
│       ├── logger.py
│       ├── main.py
│       ├── organizer.py
│       └── watcher.py
└── tests/
    ├── test_classifier.py
    ├── test_organizer.py
    └── test_watcher.py
```

### Module Responsibilities

| Module          | Responsibility                                                 |
| --------------- | -------------------------------------------------------------- |
| `classifier.py` | Determines the category and extension of supported files       |
| `config.py`     | Defines Downloads and destination directories                  |
| `organizer.py`  | Creates destinations, handles duplicate names, and moves files |
| `watcher.py`    | Monitors Downloads and manages file-processing events          |
| `logger.py`     | Configures rotating application logs                           |
| `main.py`       | Application entry point                                        |

## Logging

Application logs are stored outside Downloads at:

```text
~/.local/state/sortflow/logs/sortflow.log
```

The application uses `RotatingFileHandler` with:

* Maximum log size: 5 MiB
* Backup files: 3
* UTF-8 encoding

Keeping logs outside Downloads prevents the organizer from accidentally reacting to its own log files.

## Requirements

* Linux
* Python 3.12+
* Watchdog 6.0.0
* uv
* systemd with user-service support

The current development environment used for testing was:

```text
OS:       Linux Mint 22.3 Zena Xfce
Python:   3.12.3
uv:       0.12.7
Watchdog: 6.0.0
pytest:   9.1.1
CPU:      Intel Core i5-1035G1
RAM:      8 GB
```

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd sortflow
```

Install the project dependencies with uv:

```bash
uv sync
```

## Running Manually

The application can be started with:

```bash
uv run python -m sortflow.main
```

The program then continues running and monitors `~/Downloads`.

Stop it with:

```text
Ctrl+C
```

## Running as a systemd User Service

The organizer can run headlessly in the background using a `systemd --user` service.

The service is configured to launch:

```bash
uv run python -m sortflow.main
```

After installing the service:

```bash
systemctl --user daemon-reload
systemctl --user start sortflow.service
```

Check its status with:

```bash
systemctl --user status sortflow.service
```

Enable automatic startup:

```bash
systemctl --user enable sortflow.service
```

Once enabled, the organizer starts automatically with the user's Linux session without requiring an open terminal.

### Service Management

Restart after changing the application:

```bash
systemctl --user restart sortflow.service
```

Stop the service:

```bash
systemctl --user stop sortflow.service
```

View systemd logs:

```bash
journalctl --user -u sortflow.service
```

Follow the service log live:

```bash
journalctl --user -u sortflow.service -f
```

Application-specific logs remain in:

```text
~/.local/state/sortflow/logs/sortflow.log
```

## Testing

The project uses `pytest` for automated testing.

Run the test suite with:

```bash
uv run pytest
```

Current test result:

```text
15 passed in 0.13s
```

The test suite covers file classification, duplicate destination handling, actual file movement, Downloads path validation, file stability, and missing-file behavior.

Additional manual QA and system integration testing are documented in [`TEST_RESULTS.md`](TEST_RESULTS.md).

## Project Status

**V1.0 — Functional**

The current implementation is running as a `systemd --user` background service and has passed the current automated tests, manual QA tests, and systemd integration testing.

## Known Limitations

### Stability is based on file size

The current stability check determines that a file is stable when its size remains unchanged for the configured number of checks.

This does not guarantee that every possible application has completely finished writing to the file.

### File classification is extension-based

Classification currently relies on the file extension.

For example:

```text
report.pdf → Documents
photo.jpg  → Pictures
```

The application does not inspect file contents to determine their type.

### Categories are currently predefined

The destination categories and extensions are currently defined in the source code rather than being user-configurable.

### No content-based organization

The V1 organizer does not determine whether a document is a school file, personal file, work file, etc.

A future version could potentially introduce smarter classification rules or metadata/content-based organization.

## Future Improvements

Possible future improvements include:

* Add more supported file extensions
* Make categories configurable
* Make the Downloads directory configurable
* Improve file stability detection
* Improve graceful shutdown handling
* Expand automated integration testing
* Improve sorting performance where applicable
* Add smarter organization rules
* Support organizing files into higher-level groups such as school, personal, or other user-defined categories
* Improve configuration management

## Why I Built This

I built this project to solve a small problem I personally encountered: keeping my Downloads directory organized.

At the same time, I used it as an opportunity to practice practical Python automation and software engineering concepts, including:

* Filesystem event monitoring
* Object-oriented event handlers
* Thread-safe queues
* Background worker threads
* File operations with `pathlib`
* Logging
* Error handling
* Automated testing with pytest
* Linux service management with systemd

The project is part of my broader goal of developing practical Python automation skills, particularly for future work involving data processing and ETL.

## License

This project is licensed under the MIT License.