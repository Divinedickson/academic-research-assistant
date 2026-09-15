from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import Document, ResearchCollection


class ResearchCollectionSerializer(serializers.ModelSerializer):
    document_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ResearchCollection
        fields = ['id', 'name', 'description', 'document_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'document_count', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id',
            'collection',
            'title',
            'file',
            'original_filename',
            'file_size',
            'processing_status',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'collection',
            'original_filename',
            'file_size',
            'processing_status',
            'uploaded_at',
        ]
        extra_kwargs = {
            'file': {'write_only': True},
            'title': {'required': False, 'allow_blank': True},
        }

    def validate_file(self, uploaded_file):
        if uploaded_file.size == 0:
            raise serializers.ValidationError('Uploaded file is empty.')

        max_size = settings.DOCUMENT_UPLOAD_MAX_BYTES
        if uploaded_file.size > max_size:
            raise serializers.ValidationError(
                f'Uploaded file must be no larger than {max_size} bytes.',
            )

        if Path(uploaded_file.name).suffix.lower() != '.pdf':
            raise serializers.ValidationError('Uploaded file must use a .pdf extension.')

        signature = uploaded_file.read(5)
        uploaded_file.seek(0)

        if signature != b'%PDF-':
            raise serializers.ValidationError('Uploaded file does not appear to be a valid PDF.')

        return uploaded_file

    def create(self, validated_data):
        uploaded_file = validated_data['file']
        title = validated_data.get('title') or Path(uploaded_file.name).stem

        return Document.objects.create(
            collection=self.context['collection'],
            title=title,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
        )
