import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


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

# Create your models here.
