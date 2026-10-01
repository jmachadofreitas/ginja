"""PDF output through WeasyPrint, imported lazily so HTML builds don't need it."""

import logging
import os
from pathlib import Path

from .errors import DocumentError

FONT_SUBSET_NOTICE = "Using fontTools instead of HarfBuzz-Subset"


class _Collector(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def write_pdf(html: str, root: Path, path: Path) -> list[str]:
    """Render HTML to a PDF file and return WeasyPrint's warnings (e.g. unsupported CSS).

    Relative URLs resolve against the project root, as they do for the HTML output.
    WeasyPrint reports unreachable resources, such as a missing image, as errors; those fail
    the build instead of producing an incomplete PDF.
    """

    try:
        import weasyprint
    except (ImportError, OSError) as error:  # OSError: Pango or another system library is missing
        raise DocumentError("PDF rendering", f"WeasyPrint is unavailable: {error}") from error

    collector = _Collector()
    logger = logging.getLogger("weasyprint")
    logger.addHandler(collector)
    # Font subsetting through fontTools stamps fonts with the current time unless
    # SOURCE_DATE_EPOCH is set; a fixed value keeps the PDF byte-identical across builds.
    epoch_preset = "SOURCE_DATE_EPOCH" in os.environ
    os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
    try:
        document = weasyprint.HTML(string=html, base_url=root.as_uri() + "/").render()
        errors = [r.getMessage() for r in collector.records if r.levelno >= logging.ERROR]
        if errors:
            raise DocumentError("PDF rendering", "; ".join(errors))
        path.parent.mkdir(parents=True, exist_ok=True)
        document.write_pdf(path)
    except DocumentError:
        raise
    except Exception as error:
        raise DocumentError("PDF rendering", f"{type(error).__name__}: {error}") from error
    finally:
        logger.removeHandler(collector)
        if not epoch_preset:
            del os.environ["SOURCE_DATE_EPOCH"]
    warnings = [r.getMessage() for r in collector.records if r.levelno < logging.ERROR]
    # This notice is about the WeasyPrint installation, not the document, and repeats per font.
    return [message for message in warnings if not message.startswith(FONT_SUBSET_NOTICE)]
