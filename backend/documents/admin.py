from django.contrib import admin

from .models import Document, ResearchCollection


@admin.register(ResearchCollection)
class ResearchCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'created_at', 'updated_at']
    search_fields = ['name', 'owner__username', 'owner__email']
    list_filter = ['created_at', 'updated_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'collection',
        'original_filename',
        'file_size',
        'processing_status',
        'uploaded_at',
    ]
    search_fields = ['title', 'original_filename', 'collection__name']
    list_filter = ['processing_status', 'uploaded_at']
