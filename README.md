# SortFlow

A lightweight, content-aware Python automation tool that automatically organizes files added to my `~/Downloads` directory.

I originally built this project to solve a messy Downloads folder using simple file extensions. In V2, SortFlow has evolved into a deterministic, heuristic-based classification engine. Instead of blindly sorting by extension, it inspects filenames, extensions, and safely extracts supported file contents (including Lazy OCR for images) to intelligently route files into contextual categories like `School`, `Work`, or `Personal`.

## Demo

https://github.com/user-attachments/assets/3a89d40c-a57c-4bc9-85db-0f0af488a6d7

### See SortFlow in Action

A quick demonstration of SortFlow's content-aware file organization.

The video shows SortFlow processing different file formats and automatically routing them to the appropriate folders based on their **filename, file extension, and extracted content** — rather than relying solely on file extensions.

It also demonstrates OCR-based classification for image files and confidence-based fallback for files that lack sufficient classification signals.

**Demo files and expected results:**

| Demo File | Format | Expected Destination |
|---|---|---|
| `Q4_Operations_Update.pptx` | PowerPoint | `Work/` |
| `Family-Plan.png` | PNG Image | `Personal/` |
| `Enrollment_Requirements.jpg` | JPG Image | `School/` |
| `Monthly Financial Statement.pdf` | PDF | `Personal/` |
| `Software Development Project Proposal.docx` | Word Document | `Work/` |
| `cs_lecture_notes.txt` | Text File | `School/` |
| `server_cleanup_utility_script.py` | Python Source Code | `Uncategorized/` |

**Demo highlights:**
- Multi-format file classification
- Content-aware heuristic scoring
- OCR-based classification for images
- Automatic file organization
- Confidence-based `Uncategorized` fallback
- Automated processing from the Downloads folder

The demo illustrates how SortFlow handles different file formats, recognizes contextual signals, and avoids forcing uncertain files into an unrelated category.

## Features

- **Content-Aware Classification**: Uses a weighted scoring system based on filename keywords, file extensions, and document text.
- **Safe Content Extraction**: Plain-text extraction is capped at 50 KB. PDF/image processing is limited to three pages. Massive files exceeding 100MB are safely bypassed to protect memory.
- **Lazy OCR Integration**: PyMuPDF handles `.pdf`, `.jpg`, `.jpeg`, and `.png` files. If a scanned document lacks a text layer, it dynamically falls back to local Tesseract OCR.
- **Lazy Module Loading**: Heavy document-parsing libraries (`pymupdf`, `docx`, `pptx`) are imported only when their specific file types are detected, keeping idle RAM usage near zero.
- **SQLite Telemetry**: Logs classification decisions, confidence scores, and matched keywords to a local database for continuous heuristic tuning.
- **Deterministic & Safe**: If a file fails to meet the minimum confidence threshold, it safely routes to an `Uncategorized/` folder rather than guessing.
- **Collision Handling**: Automatically renames duplicate files (e.g., `report_1.pdf`) using an atomic `os.link` no-overwrite move, preventing data from being overwritten.
- **Headless Linux Daemon**: Runs in the background as a `systemd --user` service.

## How It Organizes Files

Classification is driven by a declarative configuration file (`config.py`). SortFlow reads the file's text and filename, cleans the punctuation, and applies regex word-boundary matching to tally a score.

For example, a downloaded file named `CS101_Assignment.pdf`:
1. Extension `.pdf` matches School (+1)
2. Filename contains `assignment` (+5)
3. Content contains `course` (+4)
**Total Score: 10** → Routed to `~/Documents/School`

### Classifier Vocabulary

The keyword vocabulary is maintained in `src/sortflow/config.py` as one flat,
deterministic dictionary per category. Multi-word phrases such as `data
structure`, `job offer`, and `national id` are supported because the
classifier normalizes punctuation before applying escaped word-boundary
matching.

The current configuration contains **315 keywords**:

| Category | Keywords | Main vocabulary groups |
| --- | ---: | --- |
| School | 94 | Academic documents, university administration, research, and computer science |
| Work | 111 | Employment, business, freelancing, OJT, and professional software |
| Personal | 110 | Identity, finance, shopping, health, personal life, and media |

Weights range from `1` for generic supporting words to `5` for highly
discriminative signals such as `professor`, `payslip`, `job offer`, `PhilSys`,
and `birth certificate`. Extensions contribute only `+1`, so `.pdf`, `.docx`,
and other shared formats cannot decide a category by themselves.

### Destination Structure

The resulting directory structure organizes by Category, then by format:

```text
~/Documents/
├── School/
│   └── [AUTOMATED]-moved-files/
│       ├── pdf/
│       └── docx/
├── Work/
│   └── [AUTOMATED]-moved-files/
│       ├── csv/
│       └── xlsx/
├── Personal/
│   └── [AUTOMATED]-moved-files/
│       └── jpg/
└── Uncategorized/
    └── [AUTOMATED]-moved-files/
        └── png/
```

## How It Works

The application follows a decoupled, event-driven data pipeline:

```text
                 ~/Downloads
                      │
              Watchdog Observer
                      │
              filesystem event
                      ▼
                 Event Queue
                      │
               Worker Thread
                      │
              Content Extractor (Limits memory, triggers Lazy OCR)
                      │
             Heuristic Classifier (Scores keywords & metadata)
                      │
             ┌────────┼────────┐
             ▼        ▼        ▼
           School    Work   Personal  (or Uncategorized)
                      │
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

The organizer therefore waits until both the file size and modification time remain unchanged for several consecutive checks before processing it. A file that never stabilizes is abandoned after 60 seconds so it cannot block the worker forever.

The current implementation uses:

* 3 stable checks
* 1 second between checks

This means the default stability requirement is based on the size and modification time remaining unchanged across consecutive observations. If another event arrives for a path that is already queued, SortFlow marks it dirty and checks it again after the current attempt finishes.

## Project Structure

```text
sortflow/
├── pyproject.toml
├── README.md
├── src/
│   └── sortflow/
│       ├── __init__.py
│       ├── classifier.py     # Weighted keyword scoring engine
│       ├── config.py         # Declarative categories and weights
│       ├── extractor.py      # Safe text reading and Lazy OCR
│       ├── logger.py         # Rotating application logs
│       ├── main.py           # Application entry point
│       ├── organizer.py      # Collision resolution and file movement
│       ├── watcher.py        # Thread-safe Watchdog event queue
│       └── database/
│           ├── connection.py # SQLite context manager
│           ├── initialize.py # Table schema definitions
│           └── repository.py # Telemetry insert queries
└── tests/
    ├── test_classifier.py
    ├── test_database.py
    ├── test_extractor.py
    ├── test_organizer.py
    └── test_watcher.py
```

## Logging & Telemetry

**Application Logs:** Stored at `~/.local/state/sortflow/logs/sortflow.log` using a `RotatingFileHandler` (max 5MB, 3 backups).

**SQLite Telemetry:** Stored at `~/.local/share/sortflow/database.db`. You can query this database to tune your configuration:

```sql
SELECT filename, predicted_category, confidence_score, matched_signals 
FROM classification_feedback 
WHERE predicted_category = 'uncategorized';
```

## Requirements

* Linux
* Python 3.12+
* `tesseract-ocr` (System-level dependency for Lazy OCR)
* Watchdog 6.0.0, PyMuPDF, python-docx, python-pptx
* uv (Python package manager)
* systemd (for user-service background execution)

## Installation

1. Install system dependencies for OCR:
```bash
sudo apt update && sudo apt install tesseract-ocr
```


2. Clone the repository:
```bash
git clone <repository-url>
cd sortflow
```


3. Install project dependencies with `uv`:
```bash
uv sync
```



## Running as a systemd User Service

After defining your service file to launch `uv run sortflow`:

```bash
systemctl --user daemon-reload
systemctl --user enable --now sortflow.service
```

Check its status or view live logs:

```bash
systemctl --user status sortflow.service
journalctl --user -u sortflow.service -f
```

## Testing

The project uses `pytest` with string-based `monkeypatching` to isolate the filesystem and bypass heavy OCR libraries during test execution.

```bash
uv run pytest
```

Additional manual QA and system integration testing are documented in [`TEST_RESULTS.md`](TEST_RESULTS.md).

## Why I Built This

I am Chyrus Miguel D. Macalla, a Computer Science student at Pampanga State University (Bacolor Campus). I built this project to solve my own cluttered `~/Downloads` directory, but engineered it explicitly for the hardware constraints of my Dell Inspiron 3593 (Intel Core i5-1035G1, 8GB RAM) running Linux Mint 22.3 XFCE. 

Because SortFlow runs continuously as a background daemon, I chose a deterministic, rule-based approach and deferred heavy module imports until absolutely necessary. This prevents unnecessary thermal throttling and leaves memory free for my active development workflows.

You can view my full engineering portfolio at: [https://migelitz.github.io/](https://migelitz.github.io/)

## License

This project is licensed under the MIT License.
