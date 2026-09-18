"""Local digital-PDF and OCR document extraction."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytesseract
from PIL import Image
from pypdf import PdfReader

from underwriteflow.providers.schemas import DocumentPage, LocalDocument


class ExtractionError(ValueError):
    """Raised when local document text cannot be safely extracted."""


class LocalDocumentExtractor:
    """Extract digital PDF text and OCR scanned PDFs or images locally."""

    # Configure the local OCR process timeout.
    def __init__(self, timeout_seconds: float = 30) -> None:
        self.timeout_seconds = timeout_seconds

    # Select the local extraction path from the persisted content type.
    def extract(self, path: Path, content_type: str) -> LocalDocument:
        if content_type == "application/pdf":
            return self._extract_pdf(path)
        if content_type in {"image/jpeg", "image/png"}:
            return self._extract_image(path)
        raise ExtractionError("unsupported document type")

    # Extract text from a digital PDF or fall back to local OCR for scans.
    def _extract_pdf(self, path: Path) -> LocalDocument:
        try:
            pages = [
                DocumentPage(
                    page_number=index,
                    text=page.extract_text() or "",
                    source_locator=f"page:{index}",
                )
                for index, page in enumerate(PdfReader(str(path)).pages, 1)
            ]
        except Exception as error:
            raise ExtractionError("PDF extraction failed") from error
        if not pages:
            raise ExtractionError("PDF contains no pages")
        if any(page.text.strip() for page in pages):
            return LocalDocument(pages=pages, method="pdf_text")
        return self._ocr_pdf(path)

    # Rasterize scanned PDF pages and OCR each generated image locally.
    def _ocr_pdf(self, path: Path) -> LocalDocument:
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "page"
            try:
                subprocess.run(
                    ["pdftoppm", "-png", "-r", "150", str(path), str(prefix)],
                    check=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                )
            except (
                FileNotFoundError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ) as error:
                raise ExtractionError("PDF OCR is unavailable") from error
            image_paths = sorted(Path(directory).glob("page-*.png"))
            if not image_paths:
                raise ExtractionError("PDF OCR produced no pages")
            pages = []
            for page_number, image_path in enumerate(image_paths, 1):
                try:
                    with Image.open(image_path) as image:
                        text = pytesseract.image_to_string(image)
                except (
                    OSError,
                    ValueError,
                    pytesseract.TesseractError,
                ) as error:
                    raise ExtractionError("PDF OCR failed") from error
                pages.append(
                    DocumentPage(
                        page_number=page_number,
                        text=text,
                        source_locator=f"page:{page_number}",
                    )
                )
            return LocalDocument(pages=pages, method="ocr")

    # OCR one supported image locally and retain its page locator.
    def _extract_image(self, path: Path) -> LocalDocument:
        try:
            with Image.open(path) as image:
                text = pytesseract.image_to_string(image)
        except (OSError, ValueError, pytesseract.TesseractError) as error:
            raise ExtractionError("image OCR failed") from error
        return LocalDocument(
            pages=[
                DocumentPage(
                    page_number=1,
                    text=text,
                    source_locator="page:1",
                )
            ],
            method="ocr",
        )
