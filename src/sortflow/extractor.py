import logging
from pathlib import Path

from sortflow.config import (
    IMAGE_EXTENSIONS,
    MAX_INPUT_BYTES,
    MAX_PAGES,
    MAX_PARAGRAPHS,
    MAX_READ_BYTES,
    MIN_TEXT_THRESHOLD,
    PLAIN_TEXT_EXTENSIONS,
)

logger = logging.getLogger(__name__)


def _extract_plain_text(path: Path) -> str:
    # Slice bytes before decoding so multibyte UTF-8 content cannot exceed the
    # intended 50 KB input budget.
    return path.read_bytes()[:MAX_READ_BYTES].decode("utf-8", errors="ignore")


def _extract_document_text(document, path: Path) -> str:
    # Limit pages examined, while keeping the document context manager owned by
    # the caller so native PyMuPDF resources are released deterministically.
    text_content = []
    for page_num in range(min(MAX_PAGES, len(document))):
        page = document[page_num]
        page_text = page.get_text()

        # Lazy OCR Trigger: If it's a raw image or a scanned PDF with no text layer
        if len(page_text.strip()) < MIN_TEXT_THRESHOLD:
            page_text = _extract_ocr_text(page, page_text, page_num, path)

        text_content.append(page_text)

    return " ".join(text_content)


def _extract_page_text(path: Path) -> str:
    # Lazy import
    import pymupdf

    with pymupdf.open(path) as source:
        # If the file is a raw image, convert it to a lightweight
        # in-memory PDF so the PyMuPDF OCR engine accepts it.
        if source.is_pdf:
            return _extract_document_text(source, path)

        pdf_bytes = source.convert_to_pdf()
        # This must be a separate context: assigning a new document over
        # `source` would leave the converted native document unclosed.
        with pymupdf.open("pdf", pdf_bytes) as document:
            return _extract_document_text(document, path)


def _extract_ocr_text(page, page_text: str, page_num: int, path: Path) -> str:
    logger.debug(
        "Insufficient text on page %d of %s. Triggering Lazy OCR.",
        page_num,
        path.name,
    )
    try:
        textpage = page.get_textpage_ocr(flags=0, language="eng", dpi=150)
        return page.get_text(textpage=textpage)
    except Exception as ocr_error:
        logger.warning(
            "OCR failed on %s: %s. Is tesseract-ocr installed?",
            path.name,
            ocr_error,
        )
        return page_text


def _extract_docx_text(path: Path) -> str:
    # Lazy import
    import docx

    document = docx.Document(path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs[:MAX_PARAGRAPHS]]
    return " ".join(paragraphs)


def _extract_pptx_text(path: Path) -> str:
    # Lazy import
    import pptx

    presentation = pptx.Presentation(path)
    text_content = []
    for slide in list(presentation.slides)[:MAX_PAGES]:
        text_content.extend(shape.text for shape in slide.shapes if hasattr(shape, "text"))
    return " ".join(text_content)


def extract_text(path: Path) -> str:
    """Extract a lowercase text preview from a supported file."""
    extension = path.suffix.lower()

    try:
        # Check before dispatching to docx/pptx/PyMuPDF, because those parsers
        # can allocate based on the full package/image before our output limits.
        if path.stat().st_size > MAX_INPUT_BYTES:
            logger.warning("Skipping oversized file: %s", path.name)
            return ""

        if extension in PLAIN_TEXT_EXTENSIONS:
            text_content = _extract_plain_text(path)
        elif extension in IMAGE_EXTENSIONS:
            text_content = _extract_page_text(path)
        elif extension == ".docx":
            text_content = _extract_docx_text(path)
        elif extension == ".pptx":
            text_content = _extract_pptx_text(path)
        else:
            text_content = ""

    except PermissionError:
        logger.warning("Permission denied reading content of %s", path.name)
        return ""
    except Exception as e:
        logger.exception("Unexpected error reading %s: %s", path.name, e)
        return ""

    return text_content.lower()
