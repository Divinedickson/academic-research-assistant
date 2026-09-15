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
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Document, DocumentChunk, ResearchCollection
from .services import PdfExtractionError, chunk_pages, extract_pdf_pages, process_document
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
            {'page_number', 'chunk_index', 'content', 'character_count'},
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
