import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Document, ResearchCollection


User = get_user_model()


def pdf_file(name='paper.pdf', content=None):
    return SimpleUploadedFile(
        name,
        content if content is not None else b'%PDF-1.7\nsample content',
        content_type='application/pdf',
    )


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

# Create your tests here.
