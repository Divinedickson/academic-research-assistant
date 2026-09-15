from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Document


@receiver(post_delete, sender=Document)
def delete_document_file(sender, instance, **kwargs):
    if instance.file and instance.file.storage.exists(instance.file.name):
        instance.file.storage.delete(instance.file.name)
