import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Document, DocumentChunk, ResearchCollection
from .services import (
    EmbeddingError,
    PdfExtractionError,
    chunk_pages,
    embed_document,
    extract_pdf_pages,
    process_document,
    semantic_search_collection,
)
from .services.extraction import ExtractedPage


User = get_user_model()


def pdf_file(name='paper.pdf', content=None):
    return SimpleUploadedFile(
        name,
        content if content is not None else b'%PDF-1.7\nsample content',
        content_type='application/pdf',
    )


def create_pdf_bytes(page_texts):
    pdf = fitz.open()

    for text in page_texts:
        page = pdf.new_page()

        if text:
            page.insert_text((72, 72), text)

    content = pdf.tobytes()
    pdf.close()
    return content


def create_pdf_file(path, page_texts):
    path.write_bytes(create_pdf_bytes(page_texts))
    return path


def vector(first_value=1.0, second_value=0.0):
    values = [0.0] * 384
    values[0] = first_value
    values[1] = second_value
    return values


class FakeEmbeddingProvider:
    model_name = 'fake-embedding-model'
    dimensions = 384

    def __init__(self, vectors=None, fail=False):
        self.vectors = vectors or []
        self.fail = fail
        self.calls = []

    def embed_texts(self, texts):
        self.calls.append(list(texts))

        if self.fail:
            raise RuntimeError('provider exploded')

        if self.vectors:
            start = sum(len(call) for call in self.calls[:-1])
            return self.vectors[start:start + len(texts)]

        return [vector() for _text in texts]


class DocumentApiTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='ResearchPass123!',
        )
        self.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='ResearchPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def create_collection(self, owner=None, name='Machine Learning'):
        return ResearchCollection.objects.create(
            owner=owner or self.user,
            name=name,
            description='Important papers',
        )

    def test_collection_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse('collection-list'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_document_endpoints_require_authentication(self):
        collection = self.create_collection()
        document = Document.objects.create(
            collection=collection,
            title='Paper',
            file=pdf_file(),
            original_filename='paper.pdf',
            file_size=20,
        )
        self.client.force_authenticate(user=None)

        list_response = self.client.get(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
        )
        detail_response = self.client.get(
            reverse('document-detail', kwargs={'pk': document.id}),
        )

        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(detail_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_list_update_and_delete_collection(self):
        create_response = self.client.post(
            reverse('collection-list'),
            {'name': 'Literature Review', 'description': 'Core sources', 'owner': self.other_user.id},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        collection = ResearchCollection.objects.get(id=create_response.data['id'])
        self.assertEqual(collection.owner, self.user)

        list_response = self.client.get(reverse('collection-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        update_response = self.client.patch(
            reverse('collection-detail', kwargs={'pk': collection.id}),
            {'name': 'Updated Review'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        collection.refresh_from_db()
        self.assertEqual(collection.name, 'Updated Review')

        delete_response = self.client.delete(
            reverse('collection-detail', kwargs={'pk': collection.id}),
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResearchCollection.objects.filter(id=collection.id).exists())

    def test_user_ownership_isolation_for_collections(self):
        own_collection = self.create_collection(name='Mine')
        other_collection = self.create_collection(owner=self.other_user, name='Theirs')

        list_response = self.client.get(reverse('collection-list'))
        detail_response = self.client.get(
            reverse('collection-detail', kwargs={'pk': other_collection.id}),
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in list_response.data], [own_collection.id])
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_pdf_upload(self):
        collection = self.create_collection()

        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'title': 'Attention Paper', 'file': pdf_file('attention.pdf')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(id=response.data['id'])
        self.assertEqual(document.collection, collection)
        self.assertEqual(document.title, 'Attention Paper')
        self.assertEqual(document.original_filename, 'attention.pdf')
        self.assertEqual(document.processing_status, Document.ProcessingStatus.UPLOADED)
        self.assertTrue(document.file.name.startswith(f'documents/user_{self.user.id}/'))
        self.assertTrue(document.file.storage.exists(document.file.name))

    def test_non_pdf_extension_is_rejected(self):
        collection = self.create_collection()

        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('paper.txt')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_fake_pdf_extension_is_rejected(self):
        collection = self.create_collection()

        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('paper.pdf', b'not a pdf')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_empty_pdf_is_rejected(self):
        collection = self.create_collection()

        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('empty.pdf', b'')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    @override_settings(DOCUMENT_UPLOAD_MAX_BYTES=10)
    def test_oversized_pdf_is_rejected(self):
        collection = self.create_collection()

        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('large.pdf', b'%PDF-1.7 oversized')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)

    def test_document_deletion_removes_stored_file(self):
        collection = self.create_collection()
        upload_response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('delete-me.pdf')},
            format='multipart',
        )
        document = Document.objects.get(id=upload_response.data['id'])
        stored_path = document.file.name

        response = self.client.delete(reverse('document-detail', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=document.id).exists())
        self.assertFalse(document.file.storage.exists(stored_path))

    def test_collection_delete_cascades_documents_and_removes_stored_files(self):
        collection = self.create_collection()
        upload_response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': collection.id}),
            {'file': pdf_file('cascade.pdf')},
            format='multipart',
        )
        document = Document.objects.get(id=upload_response.data['id'])
        stored_path = document.file.name

        response = self.client.delete(reverse('collection-detail', kwargs={'pk': collection.id}))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=document.id).exists())
        self.assertFalse(document.file.storage.exists(stored_path))

    def test_other_users_collection_and_document_return_404(self):
        other_collection = self.create_collection(owner=self.other_user, name='Private')
        other_document = Document.objects.create(
            collection=other_collection,
            title='Private Paper',
            file=pdf_file('private.pdf'),
            original_filename='private.pdf',
            file_size=20,
        )

        collection_response = self.client.get(
            reverse('collection-detail', kwargs={'pk': other_collection.id}),
        )
        nested_documents_response = self.client.get(
            reverse('collection-documents', kwargs={'collection_id': other_collection.id}),
        )
        document_response = self.client.get(
            reverse('document-detail', kwargs={'pk': other_document.id}),
        )

        self.assertEqual(collection_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nested_documents_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(document_response.status_code, status.HTTP_404_NOT_FOUND)


class PdfExtractionServiceTests(APITestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_successful_multi_page_pdf_extraction_uses_one_based_page_numbers(self):
        file_path = create_pdf_file(
            self.temp_path / 'multi.pdf',
            ['First page text.', 'Second page text.'],
        )

        pages, page_count = extract_pdf_pages(file_path)

        self.assertEqual(page_count, 2)
        self.assertEqual([page.page_number for page in pages], [1, 2])
        self.assertIn('First page text.', pages[0].content)
        self.assertIn('Second page text.', pages[1].content)

    def test_blank_pages_are_skipped_without_failing(self):
        file_path = create_pdf_file(
            self.temp_path / 'blank.pdf',
            ['First page text.', '', 'Third page text.'],
        )

        pages, page_count = extract_pdf_pages(file_path)

        self.assertEqual(page_count, 3)
        self.assertEqual([page.page_number for page in pages], [1, 3])

    def test_empty_text_or_scanned_pdf_fails_with_clear_message(self):
        file_path = create_pdf_file(self.temp_path / 'scanned.pdf', ['', ''])

        with self.assertRaises(PdfExtractionError) as error:
            extract_pdf_pages(file_path)

        self.assertIn('OCR is not available', str(error.exception))


class ChunkingServiceTests(APITestCase):
    def test_text_shorter_than_one_chunk_creates_single_chunk(self):
        chunks = chunk_pages(
            [ExtractedPage(page_number=1, content='Short text.')],
            chunk_size=1000,
            overlap=200,
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 1)
        self.assertEqual(chunks[0].chunk_index, 0)

    def test_chunking_is_deterministic(self):
        pages = [ExtractedPage(page_number=1, content='Alpha beta gamma. ' * 100)]

        first_run = chunk_pages(pages, chunk_size=120, overlap=25)
        second_run = chunk_pages(pages, chunk_size=120, overlap=25)

        self.assertEqual(first_run, second_run)

    def test_chunk_overlap_is_applied(self):
        text = ''.join(str(index % 10) for index in range(140))

        chunks = chunk_pages(
            [ExtractedPage(page_number=1, content=text)],
            chunk_size=50,
            overlap=10,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].content[-10:], chunks[1].content[:10])

    def test_very_long_paragraphs_are_split_without_empty_chunks(self):
        chunks = chunk_pages(
            [ExtractedPage(page_number=2, content='A' * 2500)],
            chunk_size=1000,
            overlap=200,
        )

        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(chunk.content for chunk in chunks))
        self.assertTrue(all(chunk.page_number == 2 for chunk in chunks))

    def test_chunking_does_not_create_empty_chunks_for_blank_pages(self):
        chunks = chunk_pages(
            [
                ExtractedPage(page_number=1, content='   '),
                ExtractedPage(page_number=2, content='Usable text.'),
            ],
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 2)


class DocumentProcessingApiTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username='processor',
            email='processor@example.com',
            password='ResearchPass123!',
        )
        self.other_user = User.objects.create_user(
            username='other-processor',
            email='other-processor@example.com',
            password='ResearchPass123!',
        )
        self.collection = ResearchCollection.objects.create(owner=self.user, name='Papers')
        self.client.force_authenticate(user=self.user)

    def create_document(self, page_texts=None, owner=None):
        owner = owner or self.user
        collection = (
            self.collection
            if owner == self.user
            else ResearchCollection.objects.create(owner=owner, name='Other Papers')
        )
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        file_path = create_pdf_file(
            Path(temp_dir.name) / 'paper.pdf',
            page_texts if page_texts is not None else ['First page text.', 'Second page text.'],
        )

        with file_path.open('rb') as handle:
            return Document.objects.create(
                collection=collection,
                title='Paper',
                file=File(handle, name='paper.pdf'),
                original_filename='paper.pdf',
                file_size=file_path.stat().st_size,
            )

    def test_successful_processing_status_transitions_and_chunks(self):
        document = self.create_document(['Page one text.' * 30, 'Page two text.' * 30])

        response = self.client.post(reverse('document-process', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.processing_status, Document.ProcessingStatus.READY)
        self.assertEqual(document.page_count, 2)
        self.assertIsNotNone(document.processed_at)
        self.assertEqual(document.processing_error, '')
        self.assertEqual(document.chunks.count(), 2)
        self.assertEqual(list(document.chunks.values_list('page_number', flat=True)), [1, 2])

    def test_failed_processing_status_transition_for_scanned_pdf(self):
        document = self.create_document(['', ''])

        response = self.client.post(reverse('document-process', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.processing_status, Document.ProcessingStatus.FAILED)
        self.assertIn('OCR is not available', document.processing_error)
        self.assertEqual(document.chunks.count(), 0)

    def test_reprocessing_replaces_old_chunks_without_duplicates(self):
        document = self.create_document(['Initial text. ' * 20])
        process_document(document)
        first_chunk_ids = list(document.chunks.values_list('id', flat=True))

        response = self.client.post(reverse('document-process', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.processing_status, Document.ProcessingStatus.READY)
        self.assertEqual(document.chunks.count(), 1)
        self.assertNotEqual(first_chunk_ids, list(document.chunks.values_list('id', flat=True)))

    def test_transaction_rollback_prevents_partial_chunks_after_failure(self):
        document = self.create_document(['Rollback text. ' * 30])

        def create_then_fail(chunks):
            DocumentChunk.objects.create(
                document=document,
                page_number=1,
                chunk_index=99,
                content='partial',
                character_count=7,
            )
            raise RuntimeError('database failed')

        with patch('documents.services.processing.DocumentChunk.objects.bulk_create', create_then_fail):
            response = self.client.post(reverse('document-process', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.processing_status, Document.ProcessingStatus.FAILED)
        self.assertEqual(document.chunks.count(), 0)
        self.assertNotIn('database failed', document.processing_error)

    def test_processing_and_chunks_require_authentication(self):
        document = self.create_document()
        self.client.force_authenticate(user=None)

        process_response = self.client.post(reverse('document-process', kwargs={'pk': document.id}))
        chunks_response = self.client.get(reverse('document-chunks', kwargs={'pk': document.id}))

        self.assertEqual(process_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(chunks_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_processing_and_chunks_enforce_ownership(self):
        other_document = self.create_document(owner=self.other_user)

        process_response = self.client.post(
            reverse('document-process', kwargs={'pk': other_document.id}),
        )
        chunks_response = self.client.get(
            reverse('document-chunks', kwargs={'pk': other_document.id}),
        )

        self.assertEqual(process_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(chunks_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_chunk_endpoint_is_read_only(self):
        document = self.create_document(['Chunk endpoint text.'])
        process_document(document)

        get_response = self.client.get(reverse('document-chunks', kwargs={'pk': document.id}))
        post_response = self.client.post(
            reverse('document-chunks', kwargs={'pk': document.id}),
            {'content': 'client chunk'},
            format='json',
        )

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(post_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            set(get_response.data[0].keys()),
            {'id', 'page_number', 'chunk_index', 'content', 'character_count'},
        )

    def test_document_processing_fields_are_read_only(self):
        response = self.client.post(
            reverse('collection-documents', kwargs={'collection_id': self.collection.id}),
            {
                'file': pdf_file('readonly.pdf', create_pdf_bytes(['Read only fields.'])),
                'processing_status': Document.ProcessingStatus.READY,
                'page_count': 99,
                'processing_error': 'client error',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(id=response.data['id'])
        self.assertEqual(document.processing_status, Document.ProcessingStatus.UPLOADED)
        self.assertEqual(document.page_count, 0)
        self.assertEqual(document.processing_error, '')
        self.assertIsNone(document.processed_at)


class EmbeddingAndSearchTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username='embedder',
            email='embedder@example.com',
            password='ResearchPass123!',
        )
        self.other_user = User.objects.create_user(
            username='other-embedder',
            email='other-embedder@example.com',
            password='ResearchPass123!',
        )
        self.collection = ResearchCollection.objects.create(owner=self.user, name='Embedding Papers')
        self.other_collection = ResearchCollection.objects.create(
            owner=self.other_user,
            name='Private Embedding Papers',
        )
        self.client.force_authenticate(user=self.user)

    def create_ready_document(self, collection=None, title='Ready Paper', chunk_texts=None):
        collection = collection or self.collection
        document = Document.objects.create(
            collection=collection,
            title=title,
            file=pdf_file('ready.pdf', create_pdf_bytes(['Ready text.'])),
            original_filename='ready.pdf',
            file_size=20,
            processing_status=Document.ProcessingStatus.READY,
            page_count=1,
            processed_at=timezone.now(),
        )
        if chunk_texts is None:
            chunk_texts = ['first chunk', 'second chunk']

        for index, content in enumerate(chunk_texts):
            DocumentChunk.objects.create(
                document=document,
                page_number=index + 1,
                chunk_index=index,
                content=content,
                character_count=len(content),
            )

        return document

    def test_fake_embedding_provider_batches_and_dimensions(self):
        provider = FakeEmbeddingProvider(vectors=[vector(), vector(0.0, 1.0), vector(1.0, 1.0)])

        embeddings = provider.embed_texts(['a', 'b'])
        more_embeddings = provider.embed_texts(['c'])

        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(len(embeddings[0]), 384)
        self.assertEqual(more_embeddings[0][0], 1.0)

    def test_embedding_vectors_are_normalized_before_storage(self):
        document = self.create_ready_document(chunk_texts=['one'])
        provider = FakeEmbeddingProvider(vectors=[vector(3.0, 4.0)])

        embed_document(document, provider=provider)

        chunk = document.chunks.get()
        self.assertAlmostEqual(chunk.embedding[0], 0.6)
        self.assertAlmostEqual(chunk.embedding[1], 0.8)

    def test_embedding_rejects_wrong_vector_dimensions(self):
        document = self.create_ready_document(chunk_texts=['one'])
        provider = FakeEmbeddingProvider(vectors=[[1.0, 0.0]])

        with self.assertRaises(EmbeddingError):
            embed_document(document, provider=provider)

        document.refresh_from_db()
        self.assertEqual(document.embedding_status, Document.EmbeddingStatus.FAILED)
        self.assertFalse(document.chunks.filter(embedding__isnull=False).exists())

    def test_embedding_only_ready_documents(self):
        document = self.create_ready_document()
        document.processing_status = Document.ProcessingStatus.UPLOADED
        document.save(update_fields=['processing_status'])

        with self.assertRaises(EmbeddingError):
            embed_document(document, provider=FakeEmbeddingProvider())

    def test_embedding_rejects_document_without_chunks(self):
        document = self.create_ready_document(chunk_texts=[])
        document.chunks.all().delete()

        with self.assertRaises(EmbeddingError):
            embed_document(document, provider=FakeEmbeddingProvider())

    def test_successful_embedding_of_all_chunks_in_batches(self):
        document = self.create_ready_document(chunk_texts=['a', 'b', 'c'])
        provider = FakeEmbeddingProvider(vectors=[vector(), vector(0.0, 1.0), vector(1.0, 1.0)])

        embed_document(document, provider=provider, batch_size=2)

        document.refresh_from_db()
        self.assertEqual(document.embedding_status, Document.EmbeddingStatus.EMBEDDED)
        self.assertEqual([len(call) for call in provider.calls], [2, 1])
        self.assertEqual(document.chunks.filter(embedding__isnull=False).count(), 3)
        self.assertTrue(document.chunks.filter(embedding_model=provider.model_name).count(), 3)

    def test_safe_re_embedding_replaces_vectors(self):
        document = self.create_ready_document(chunk_texts=['a'])
        embed_document(document, provider=FakeEmbeddingProvider(vectors=[vector()]))
        first_embedding = list(document.chunks.get().embedding)

        embed_document(document, provider=FakeEmbeddingProvider(vectors=[vector(0.0, 1.0)]))

        document.refresh_from_db()
        second_embedding = list(document.chunks.get().embedding)
        self.assertNotEqual(first_embedding, second_embedding)
        self.assertEqual(document.embedding_status, Document.EmbeddingStatus.EMBEDDED)

    def test_embedding_failure_keeps_old_vectors_without_mixture(self):
        document = self.create_ready_document(chunk_texts=['a', 'b'])
        embed_document(document, provider=FakeEmbeddingProvider(vectors=[vector(), vector()]))
        old_vectors = [
            list(embedding)
            for embedding in document.chunks.order_by('chunk_index').values_list('embedding', flat=True)
        ]

        with self.assertRaises(EmbeddingError):
            embed_document(document, provider=FakeEmbeddingProvider(fail=True))

        document.refresh_from_db()
        new_vectors = [
            list(embedding)
            for embedding in document.chunks.order_by('chunk_index').values_list('embedding', flat=True)
        ]
        self.assertEqual(old_vectors, new_vectors)
        self.assertEqual(document.embedding_status, Document.EmbeddingStatus.FAILED)
        self.assertNotIn('provider exploded', document.embedding_error)

    def test_embed_endpoint_authentication_and_ownership(self):
        document = self.create_ready_document()
        other_document = self.create_ready_document(collection=self.other_collection)
        self.client.force_authenticate(user=None)

        unauthenticated = self.client.post(reverse('document-embed', kwargs={'pk': document.id}))
        self.client.force_authenticate(user=self.user)
        other_response = self.client.post(reverse('document-embed', kwargs={'pk': other_document.id}))

        self.assertEqual(unauthenticated.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(other_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_embed_endpoint_success_with_fake_provider(self):
        document = self.create_ready_document(chunk_texts=['a'])

        with patch(
            'documents.views.embed_document',
            side_effect=lambda doc: embed_document(doc, provider=FakeEmbeddingProvider()),
        ):
            response = self.client.post(reverse('document-embed', kwargs={'pk': document.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['embedding_status'], Document.EmbeddingStatus.EMBEDDED)

    def test_blank_query_and_top_k_validation(self):
        blank_response = self.client.post(
            reverse('collection-search', kwargs={'collection_id': self.collection.id}),
            {'query': '   ', 'top_k': 5},
            format='json',
        )
        too_large_response = self.client.post(
            reverse('collection-search', kwargs={'collection_id': self.collection.id}),
            {'query': 'biology', 'top_k': 21},
            format='json',
        )

        self.assertEqual(blank_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(too_large_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collection_search_enforces_ownership(self):
        response = self.client.post(
            reverse('collection-search', kwargs={'collection_id': self.other_collection.id}),
            {'query': 'private'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_semantic_ranking_and_citation_metadata(self):
        document = self.create_ready_document(
            title='Neural Topic Paper',
            chunk_texts=['neural networks', 'climate systems'],
        )
        chunks = list(document.chunks.order_by('chunk_index'))
        chunks[0].embedding = vector(1.0, 0.0)
        chunks[1].embedding = vector(0.0, 1.0)
        for chunk in chunks:
            chunk.embedding_model = 'fake-embedding-model'
            chunk.embedded_at = timezone.now()
        DocumentChunk.objects.bulk_update(chunks, ['embedding', 'embedding_model', 'embedded_at'])

        results = semantic_search_collection(
            self.collection,
            'artificial intelligence',
            top_k=2,
            provider=FakeEmbeddingProvider(vectors=[vector(1.0, 0.0)]),
        )

        self.assertEqual([result.chunk_index for result in results], [0, 1])
        self.assertEqual(results[0].document_title, 'Neural Topic Paper')
        self.assertEqual(results[0].original_filename, 'ready.pdf')
        self.assertEqual(results[0].page_number, 1)
        self.assertGreater(results[0].similarity_score, results[1].similarity_score)

    def test_search_is_limited_to_selected_collection_and_embedded_chunks(self):
        selected_document = self.create_ready_document(
            collection=self.collection,
            title='Selected',
            chunk_texts=['selected embedded', 'selected unembedded'],
        )
        other_document = self.create_ready_document(
            collection=ResearchCollection.objects.create(owner=self.user, name='Other Owned'),
            title='Other Owned',
            chunk_texts=['other collection'],
        )
        private_document = self.create_ready_document(
            collection=self.other_collection,
            title='Private',
            chunk_texts=['private'],
        )

        selected_chunk = selected_document.chunks.order_by('chunk_index').first()
        selected_chunk.embedding = vector()
        selected_chunk.embedding_model = 'fake-embedding-model'
        selected_chunk.embedded_at = timezone.now()
        selected_chunk.save(update_fields=['embedding', 'embedding_model', 'embedded_at'])

        for document in [other_document, private_document]:
            chunk = document.chunks.first()
            chunk.embedding = vector()
            chunk.embedding_model = 'fake-embedding-model'
            chunk.embedded_at = timezone.now()
            chunk.save(update_fields=['embedding', 'embedding_model', 'embedded_at'])

        results = semantic_search_collection(
            self.collection,
            'selected',
            top_k=10,
            provider=FakeEmbeddingProvider(vectors=[vector()]),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document_id, selected_document.id)
        self.assertEqual(results[0].content, 'selected embedded')

    def test_empty_search_result_behavior(self):
        self.create_ready_document(chunk_texts=['not embedded'])

        results = semantic_search_collection(
            self.collection,
            'anything',
            provider=FakeEmbeddingProvider(vectors=[vector()]),
        )

        self.assertEqual(results, [])

    def test_search_endpoint_response_for_empty_results(self):
        with patch(
            'documents.views.semantic_search_collection',
            return_value=[],
        ):
            response = self.client.post(
                reverse('collection-search', kwargs={'collection_id': self.collection.id}),
                {'query': 'anything', 'top_k': 3},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [])
        self.assertIn('higher is more similar', response.data['score_description'])
