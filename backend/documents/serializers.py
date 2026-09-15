from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import Document, DocumentChunk, ResearchCollection


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
            'page_count',
            'processed_at',
            'processing_error',
            'embedding_status',
            'embedding_error',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'collection',
            'original_filename',
            'file_size',
            'processing_status',
            'page_count',
            'processed_at',
            'processing_error',
            'embedding_status',
            'embedding_error',
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


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'page_number', 'chunk_index', 'content', 'character_count']
        read_only_fields = fields


class SemanticSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=False, trim_whitespace=True)
    top_k = serializers.IntegerField(min_value=1, max_value=20, default=5)


class SemanticSearchResultSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    document_title = serializers.CharField()
    original_filename = serializers.CharField()
    page_number = serializers.IntegerField()
    chunk_index = serializers.IntegerField()
    content = serializers.CharField()
    cosine_distance = serializers.FloatField()
    similarity_score = serializers.FloatField()


class SemanticSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    top_k = serializers.IntegerField()
    score_description = serializers.CharField()
    results = SemanticSearchResultSerializer(many=True)
