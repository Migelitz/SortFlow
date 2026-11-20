# Test Results

This document records the automated tests, manual QA, system integration testing, and memory benchmarking performed on the V2 SortFlow file organizer.

The purpose of this testing is to verify that the heuristic content-scoring engine, expanded keyword vocabulary, lazy text extraction, SQLite telemetry, and background Linux service behave deterministically without causing unnecessary memory bloat or thermal throttling.

---

# Test Environment

| Component | Version / Specification |
| --- | --- |
| Operating System | Linux Mint 22.3 Zena Xfce |
| Python | 3.12.3 |
| uv | 0.12.7 (x86_64-unknown-linux-gnu) |
| Watchdog | 6.0.0 |
| pytest | 9.1.1 |
| CPU | Intel Core i5-1035G1 |
| RAM | 8 GB |
| Desktop Environment | XFCE |

---

# Automated Testing

The project uses `pytest` for unit testing with string-based `monkeypatch` targeting to decouple the core logic from the physical filesystem and heavy OCR libraries.

Tests are divided into five modules:

```text
tests/
├── test_classifier.py
├── test_database.py
├── test_extractor.py
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
==================================================== test session starts =====================================================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/migelitos/Applications/sortflow
configfile: pyproject.toml
collected 33 items

tests/test_classifier.py ................                                                                               [ 48%]
tests/test_database.py ...                                                                                             [ 57%]
tests/test_extractor.py ......                                                                                         [ 76%]
tests/test_organizer.py ...                                                                                            [ 85%]
tests/test_watcher.py .....                                                                                            [100%]

===================================================== 33 passed in 0.37s =====================================================
```

**Result: 33/33 tests passed.**

---

# Automated Test Coverage

## Classifier Tests

`test_classifier.py` verifies the weighted heuristic scoring system against simulated file names and text contents.

* Filename-only keyword matches (simulating empty content) successfully meeting the confidence threshold.

* Combined extension and content keyword matches reaching the target score.

* Ambiguous files failing to meet the `MIN_CONFIDENCE_THRESHOLD` and falling back safely to `Uncategorized`.

* Representative school, work, and personal filenames matching the expanded vocabulary.

* Weak ambiguous combinations such as `Database_Project.pdf` remaining
  uncategorized instead of being forced by one generic signal.

The vocabulary currently contains 315 weighted keywords: 94 school, 111 work,
and 110 personal terms. Strong category-specific phrases receive higher
weights, while generic terms such as `project`, `database`, and `payment`
remain low-weight supporting signals.



**Result: PASS**

---

## Extractor Tests

`test_extractor.py` verifies that the `extract_text` pipeline strictly adheres to lazy-loading design patterns and functional isolation.

* Validates through parameterized tests and a spy function that specific file extensions (`.txt`, `.pdf`, `.docx`, `.pptx`) trigger *only* their designated loader functions without executing the others.


* Validates that standard `.txt` processing does not inadvertently load heavy C-bindings into `sys.modules`.


* Ensures `pymupdf`, `docx`, and `pptx` are completely absent from RAM unless their specific file types trigger them.



**Result: PASS**

---

## Database Tests

`test_database.py` validates SQLite context management and schema generation.

* Verifies idempotent creation of the `classification_feedback` and `file_operations` tables.


* Confirms successful persistence of V2 telemetry, specifically the `confidence_score` and `matched_signals` columns.


* Validates rollback behavior on simulated operation failures.



**Result: PASS**

---

## Organizer Tests

`test_organizer.py` verifies destination collision handling and the execution of file movement using mocked `ClassificationResult` objects.

* **Initial destination:** Original filename is retained.


* **First duplicate:** `report.txt` correctly increments to `report_1.txt` without overwriting data.


* **File Movement:** Verifies the atomic `os.link()` plus source `unlink()`
  move, ensuring the source file disappears and the destination contains the
  correct data without overwriting an existing destination.



**Result: PASS**

---

## Watcher Tests

`test_watcher.py` verifies path validation and the `watchdog` event queue stability checks.

* Paths natively inside or nested deeply within `~/Downloads` are accepted.


* Paths executing outside of the targeted directory are rejected.


* Files must retain the same size and modification time across 3 consecutive
  checks (1-second intervals) before processing begins.

* Permanently changing files are abandoned after the 60-second stability
  timeout, and events received while a path is pending trigger a dirty-path
  recheck.

* Disappearing files (e.g., deleted by the user mid-download) are handled gracefully without raising unhandled exceptions.



**Result: PASS**

---

# Memory & Performance Benchmarking

A manual `tracemalloc` benchmark was executed against the text extraction pipeline to quantify the RAM savings achieved by lazy-loading the PyMuPDF and Office libraries.

Result:

```text
Starting memory tracker...
Memory to boot Extractor: 1.32 MB
Memory cost of heavy libraries: +31.39 MB
```

### Benchmark Conclusion

The base Extractor footprint uses only 1.32 MB of memory during idle continuous monitoring. By deferring the load of OCR and document-parsing dependencies, the application conserves 31.39 MB of RAM.

---

# Manual QA

Manual testing was performed against the running Watchdog application to verify real-world heuristic parsing and OCR integration.

| # | Test | Result |
| --- | --- | --- |
| 1 | Startup/shutdown logging | PASS |
| 2 | Content-aware document classification & routing | PASS |
| 3 | Lazy OCR triggered on flat images (0 native text) | PASS |
| 4 | Below-threshold files route to `Uncategorized` | PASS |
| 5 | Duplicate filename collision resolution | PASS |
| 6 | SQLite telemetry accurately reflects keyword scores | PASS |

**Manual QA Result: 6/6 PASS**

---

# systemd Integration Testing

SortFlow was integrated into Linux as a `systemd --user` background service.

## Background Operation & Automatic Startup

* The service was enabled using `systemctl --user enable sortflow.service`.
* The system was rebooted into the graphical XFCE session.
* Test files dropped into `~/Downloads` were detected, scanned, and properly routed while running completely headlessly.

**Result: PASS**

---

# Logging & Telemetry Integration

SortFlow maintains two independent logging streams outside of the monitored directory to prevent recursive Watchdog loops:

**1. Application Logging (`~/.local/state/sortflow/logs/sortflow.log`)**
Uses a `RotatingFileHandler` (max 5 MiB, 3 backups) to capture worker thread info, extraction errors, and shutdown events.

**2. SQLite Telemetry (`~/.local/share/sortflow/database.db`)**
Successfully records the reasoning logic and the final confidence score for every classified file, enabling continuous tuning of the heuristic weights.

**Result: PASS**

---

# Overall Results

| Test Category | Result |
| --- | --- |
| Automated pytest tests | 33/33 PASS |
| Manual QA | 6/6 PASS |
| Memory Benchmarking | PASS |
| systemd service startup | PASS |
| Background file organization | PASS |

## Overall Status

**V2.0 — Functional & Optimized**

The heuristic classification engine operates successfully as a headless Linux user service. Content extraction works cleanly, collision parameters are respected, and memory constraints operate exactly as designed.