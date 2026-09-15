import re
from dataclasses import dataclass

import fitz


class PdfExtractionError(Exception):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    content: str


def normalize_text(text):
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    normalized = re.sub(r'[ \t]+', ' ', normalized)
    normalized = re.sub(r' *\n *', '\n', normalized)
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized.strip()


def extract_pdf_pages(file_path):
    pages = []

    try:
        with fitz.open(file_path) as pdf:
            page_count = pdf.page_count

            for page_index, page in enumerate(pdf, start=1):
                text = normalize_text(page.get_text('text'))

                if text:
                    pages.append(ExtractedPage(page_number=page_index, content=text))
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise PdfExtractionError('The uploaded PDF could not be opened for text extraction.') from exc

    if not pages:
        raise PdfExtractionError(
            'No usable text could be extracted. Scanned or image-only PDFs are not supported yet because OCR is not available.',
        )

    return pages, page_count
