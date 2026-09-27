# Test Results

This document records the automated tests, manual QA, and system integration testing performed on the SortFlow

The purpose of this testing is to verify that the current V1 implementation behaves as expected under the tested environment and scenarios.

---

# Test Environment

| Component           | Version / Specification           |
| ------------------- | --------------------------------- |
| Operating System    | Linux Mint 22.3 Zena Xfce         |
| Python              | 3.12.3                            |
| uv                  | 0.12.7 (x86_64-unknown-linux-gnu) |
| Watchdog            | 6.0.0                             |
| pytest              | 9.1.1                             |
| CPU                 | Intel Core i5-1035G1              |
| RAM                 | 8 GB                              |
| Desktop Environment | XFCE                              |

---

# Automated Testing

The project uses `pytest` for unit testing.

Tests are divided into three modules:

```text
tests/
├── test_classifier.py
├── test_organizer.py
└── test_watcher.py
```

## Test Execution

Command:

```bash
uv run pytest
```

Result:

```text
============================================================ test session starts ============================================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/user/Applications/sortflow
configfile: pyproject.toml
collected 15 items

tests/test_classifier.py ...... [ 40%]
tests/test_organizer.py ....... [ 66%]
tests/test_watcher.py ..... [100%]

============================================================ 15 passed in 0.13s =============================================================
```

**Result: 15/15 tests passed.**

---

# Automated Test Coverage

## Classifier Tests

`test_classifier.py` verifies that supported file extensions are classified into the correct category.

Tested cases include:

* `.pdf`
* uppercase `.PDF`
* `.mp3`
* `.png`
* `.mp4`
* unsupported `.xyz`

The classifier correctly handles case-insensitive extensions and returns `None` for unsupported extensions.

**Result: PASS**

---

## Organizer Tests

`test_organizer.py` verifies destination collision handling and actual file movement.

### Initial destination

```text
report.txt
```

When no file exists at the destination, the original filename is retained.

**Result: PASS**

### First duplicate

```text
report.txt
report_1.txt
```

When `report.txt` already exists, the organizer generates `report_1.txt`.

**Result: PASS**

### Multiple duplicates

```text
report.txt
report_1.txt
report_2.txt
```

When both `report.txt` and `report_1.txt` exist, the organizer generates `report_2.txt`.

**Result: PASS**

### Actual file movement

A temporary Downloads and Documents directory was used.

Input:

```text
Downloads/report.txt
```

Expected:

```text
Documents/[AUTOMATED]-moved-files/txt/report.txt
```

The test verifies:

1. The destination file exists.
2. The file contents are preserved.
3. The original file no longer exists.

**Result: PASS**

---

## Watcher Tests

`test_watcher.py` verifies path validation and file stability behavior.

### File inside Downloads

A path directly inside the configured Downloads directory is accepted.

**Result: PASS**

### File outside Downloads

A path outside Downloads is rejected.

**Result: PASS**

### Nested path

A path inside a Downloads subdirectory is recognized as being within Downloads by the path validation function.

**Result: PASS**

The actual Watchdog observer is configured as non-recursive, so subdirectories are not monitored for filesystem events.

**Result: PASS**

### Stable file

A file whose size remains unchanged across the required checks is considered stable.

**Result: PASS**

### Missing file

A file that does not exist when stability checking begins is handled without raising an unhandled exception.

**Result: PASS**

---

# Manual QA

Manual testing was performed against the actual Watchdog application.

The purpose of manual QA was to verify behavior that is difficult or inappropriate to fully reproduce with unit tests, particularly real filesystem events and long-running behavior.

## Manual QA Summary

|  # | Test                                       | Result |
| -: | ------------------------------------------ | ------ |
|  1 | Startup/shutdown logging                   | PASS   |
|  2 | Supported file detection and organization  | PASS   |
|  3 | Unsupported extension ignored              | PASS   |
|  4 | Uppercase extension handling               | PASS   |
|  5 | Non-recursive Downloads monitoring         | PASS   |
|  6 | File stability waiting                     | PASS   |
|  7 | File moved outside Downloads while waiting | PASS   |
|  8 | Duplicate filename handling                | PASS   |
|  9 | Clean shutdown without traceback           | PASS   |

**Manual QA Result: 9/9 PASS**

---

# Manual QA Details

## 1. Startup and Shutdown Logging

The application was started manually and produced startup log entries.

Example:

```text
Initializing sortflow
Starting file watcher for: /home/user/Downloads
File watcher started successfully
```

The application also handled shutdown without producing a traceback.

**Result: PASS**

---

## 2. Supported File Organization

Supported files placed into Downloads were detected and moved into their appropriate automated destination directories.

**Result: PASS**

---

## 3. Unsupported Extensions

Files with unsupported extensions were detected but ignored.

They remained in Downloads instead of being moved.

**Result: PASS**

---

## 4. Uppercase Extensions

Files with uppercase extensions were correctly classified.

For example:

```text
REPORT.PDF
```

was treated as:

```text
.pdf
```

**Result: PASS**

---

## 5. Non-Recursive Monitoring

The application was tested with files inside subdirectories of Downloads.

The Watchdog observer is configured without recursive monitoring, so subdirectories are not actively watched for filesystem events.

**Result: PASS**

---

## 6. File Stability

The application was tested with files that were still being written.

The organizer waited for the file size to remain unchanged before attempting to organize the file.

**Result: PASS**

---

## 7. File Moved Outside Downloads While Waiting

A file was moved outside Downloads while the organizer was waiting for it to become stable.

The worker checks the path again after the stability wait.

The file was therefore skipped instead of being organized from its new location.

**Result: PASS**

---

## 8. Duplicate Filename Handling

Existing destination filenames were used to test collision handling.

The organizer generated incrementing filenames:

```text
report.txt
report_1.txt
report_2.txt
...
```

without overwriting existing files.

**Result: PASS**

---

## 9. Clean Shutdown

The application was interrupted manually.

The application logged the shutdown request and stopped the Watchdog observer without producing a traceback.

Example:

```text
Shutdown requested
File watcher stopped
```

**Result: PASS**

---

# systemd Integration Testing

After the application passed its functional tests, it was integrated into Linux as a `systemd --user` service.

The service launches the application using:

```bash
/home/user/.local/bin/uv run python -m sortflow.main
```

The project is configured as a user-level service so that it does not require root privileges.

## Service Startup

The service was started using:

```bash
systemctl --user start sortflow.service
```

The service reported:

```text
Active: active (running)
```

**Result: PASS**

## Background Operation

The service was tested while running without an interactive Python terminal.

A test file was placed into Downloads.

The organizer detected and moved the file automatically while running as a background service.

**Result: PASS**

## Automatic Startup

The service was enabled using:

```bash
systemctl --user enable sortflow.service
```

The system was logged out and back into the graphical user session.

The service started automatically after login.

**Result: PASS**

---

# Logging Integration

Application logs are stored outside Downloads at:

```text
~/.local/state/sortflow/logs/sortflow.log
```

This prevents the logging system from generating files inside the directory being monitored.

The application uses a rotating file handler with:

```text
Maximum size: 5 MiB
Backup count: 3
```

Startup and file-processing events were successfully recorded.

**Result: PASS**

---

# Overall Results

| Test Category                 |     Result |
| ----------------------------- | ---------: |
| Automated pytest tests        | 15/15 PASS |
| Manual QA                     |   9/9 PASS |
| systemd service startup       |       PASS |
| Background file organization  |       PASS |
| Automatic startup after login |       PASS |
| Logging integration           |       PASS |

## Overall Status

**V1.0 — Functional**

The current implementation successfully performs its intended file organization workflow and operates as a background Linux user service.

---

# Known Limitations

The following limitations are known in the current V1 implementation.

### File stability detection

Stability is currently determined by observing whether the file size remains unchanged for consecutive checks.

A stable file size does not mathematically guarantee that another application has completely finished writing the file.

### Extension-based classification

Files are classified according to their filename extension rather than inspecting their contents.

### Static configuration

Directories and supported extensions are currently defined in Python source code rather than through an external configuration file.

### Basic shutdown architecture

The current worker thread is designed as a long-running daemon thread. Future versions could improve shutdown coordination between the worker, queue, and Watchdog observer.

---

# Future Testing

Potential future testing improvements include:

* More automated integration tests using real filesystem events
* Tests for every supported extension
* Tests for more complex duplicate filename scenarios
* Tests involving larger files
* Tests for rapid sequences of filesystem events
* Tests for files that repeatedly change size
* Tests for service restart behavior after an application failure
* Tests for log rotation
* Performance measurements under larger workloads

---

# Conclusion

The V1 SortFlow passed all currently implemented automated tests, manual QA scenarios, and systemd integration tests in the documented environment.

The testing results establish the behavior of the current implementation under the tested scenarios rather than claiming that the application is universally optimal for every filesystem workload.
