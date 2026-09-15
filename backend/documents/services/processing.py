from django.conf import settings
from django.db import transaction

from documents.models import DocumentChunk

from .chunking import chunk_pages
from .extraction import PdfExtractionError, extract_pdf_pages


class DocumentProcessingError(Exception):
    pass


def process_document(document):
    document.mark_processing()

    try:
        pages, page_count = extract_pdf_pages(document.file.path)
        chunks = chunk_pages(
            pages,
            chunk_size=settings.DOCUMENT_CHUNK_SIZE,
            overlap=settings.DOCUMENT_CHUNK_OVERLAP,
        )

        if not chunks:
            raise DocumentProcessingError(
                'No usable text chunks could be created from this PDF.',
            )

        with transaction.atomic():
            document.chunks.all().delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        character_count=chunk.character_count,
                    )
                    for chunk in chunks
                ],
            )
            document.mark_ready(page_count=page_count)
    except (PdfExtractionError, DocumentProcessingError) as exc:
        document.chunks.all().delete()
        document.mark_failed(str(exc))
    except Exception as exc:
        document.chunks.all().delete()
        document.mark_failed('The PDF could not be processed. Please try another text-based PDF.')

    document.refresh_from_db()
    return document
