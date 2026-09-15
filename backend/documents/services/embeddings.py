import math
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from pgvector.django import CosineDistance

from documents.models import Document, DocumentChunk, ResearchCollection


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformersEmbeddingProvider:
    _model = None

    def __init__(self, model_name=None, dimensions=None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.dimensions = dimensions or settings.EMBEDDING_DIMENSIONS

    def _get_model(self):
        if self.__class__._model is None:
            from sentence_transformers import SentenceTransformer

            self.__class__._model = SentenceTransformer(self.model_name)

            model_dimensions = self.__class__._model.get_sentence_embedding_dimension()
            if model_dimensions != self.dimensions:
                raise EmbeddingError(
                    f'Embedding model returned {model_dimensions} dimensions, expected {self.dimensions}.',
                )

        return self.__class__._model

    def embed_texts(self, texts):
        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [embedding.astype(float).tolist() for embedding in embeddings]


def get_embedding_provider():
    if settings.EMBEDDING_PROVIDER != 'sentence_transformers':
        raise EmbeddingError('Configured embedding provider is not supported.')

    return SentenceTransformersEmbeddingProvider()


def _validate_embedding_dimensions(embeddings, dimensions):
    for embedding in embeddings:
        if len(embedding) != dimensions:
            raise EmbeddingError(
                f'Embedding vector has {len(embedding)} dimensions, expected {dimensions}.',
            )


def _normalize_embedding(embedding):
    norm = math.sqrt(sum(value * value for value in embedding))

    if norm == 0:
        raise EmbeddingError('Embedding provider returned a zero vector.')

    return [value / norm for value in embedding]


def embed_document(document, provider=None, batch_size=None):
    provider = provider or get_embedding_provider()
    batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

    if document.processing_status != Document.ProcessingStatus.READY:
        raise EmbeddingError('Only ready documents can be embedded.')

    chunks = list(document.chunks.order_by('chunk_index'))

    if not chunks:
        raise EmbeddingError('This document has no chunks to embed.')

    document.mark_embedding()

    try:
        embeddings = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            embeddings.extend(provider.embed_texts([chunk.content for chunk in batch]))

        _validate_embedding_dimensions(embeddings, provider.dimensions)
        normalized_embeddings = [_normalize_embedding(embedding) for embedding in embeddings]
        embedded_at = timezone.now()

        with transaction.atomic():
            for chunk, embedding in zip(chunks, normalized_embeddings, strict=True):
                chunk.embedding = embedding
                chunk.embedding_model = provider.model_name
                chunk.embedded_at = embedded_at

            DocumentChunk.objects.bulk_update(
                chunks,
                ['embedding', 'embedding_model', 'embedded_at'],
            )
            document.mark_embedded()
    except EmbeddingError as exc:
        document.mark_embedding_failed(str(exc))
        raise
    except Exception as exc:
        document.mark_embedding_failed('The document could not be embedded. Please try again.')
        raise EmbeddingError('Document embedding failed.') from exc

    document.refresh_from_db()
    return document


@dataclass(frozen=True)
class SearchResult:
    chunk_id: int
    document_id: int
    document_title: str
    original_filename: str
    page_number: int
    chunk_index: int
    content: str
    cosine_distance: float
    similarity_score: float


def semantic_search_collection(collection, query, top_k=5, provider=None):
    provider = provider or get_embedding_provider()
    query_embedding = provider.embed_texts([query])[0]
    _validate_embedding_dimensions([query_embedding], provider.dimensions)
    query_embedding = _normalize_embedding(query_embedding)

    queryset = (
        DocumentChunk.objects.filter(
            document__collection=collection,
            document__processing_status=Document.ProcessingStatus.READY,
            embedding__isnull=False,
            embedding_model=provider.model_name,
        )
        .select_related('document')
        .annotate(cosine_distance=CosineDistance('embedding', query_embedding))
        .order_by('cosine_distance', 'document_id', 'page_number', 'chunk_index')[:top_k]
    )

    return [
        SearchResult(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            original_filename=chunk.document.original_filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            cosine_distance=float(chunk.cosine_distance),
            similarity_score=1.0 - float(chunk.cosine_distance),
        )
        for chunk in queryset
    ]
