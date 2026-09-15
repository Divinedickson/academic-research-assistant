import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    owner_id = instance.collection.owner_id
    collection_id = instance.collection_id or 'new'
    return f'documents/user_{owner_id}/collection_{collection_id}/{uuid.uuid4()}{extension}'


class ResearchCollection(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='research_collections',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return self.name


class Document(models.Model):
    class ProcessingStatus(models.TextChoices):
        UPLOADED = 'uploaded', 'Uploaded'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    collection = models.ForeignKey(
        ResearchCollection,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
    )
    page_count = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        storage = self.file.storage if self.file else None
        path = self.file.name if self.file else None
        result = super().delete(*args, **kwargs)

        if storage and path and storage.exists(path):
            storage.delete(path)

        return result

    def mark_processing(self):
        self.processing_status = self.ProcessingStatus.PROCESSING
        self.processing_error = ''
        self.save(update_fields=['processing_status', 'processing_error'])

    def mark_ready(self, page_count):
        self.processing_status = self.ProcessingStatus.READY
        self.page_count = page_count
        self.processing_error = ''
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                'processing_status',
                'page_count',
                'processing_error',
                'processed_at',
            ],
        )

    def mark_failed(self, message):
        self.processing_status = self.ProcessingStatus.FAILED
        self.processing_error = message
        self.processed_at = timezone.now()
        self.save(update_fields=['processing_status', 'processing_error', 'processed_at'])


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks',
    )
    page_number = models.PositiveIntegerField()
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    character_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document_id', 'chunk_index']
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'chunk_index'],
                name='unique_chunk_index_per_document',
            ),
        ]

    def __str__(self):
        return f'{self.document_id}:{self.chunk_index}'
