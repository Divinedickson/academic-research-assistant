from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ResearchCollection
from .serializers import DocumentChunkSerializer, DocumentSerializer, ResearchCollectionSerializer
from .services import process_document


class ResearchCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = ResearchCollectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return (
            ResearchCollection.objects.filter(owner=self.request.user)
            .annotate(document_count=Count('documents'))
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class CollectionDocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_collection(self):
        return generics.get_object_or_404(
            ResearchCollection,
            id=self.kwargs['collection_id'],
            owner=self.request.user,
        )

    def get_queryset(self):
        return Document.objects.filter(collection=self.get_collection())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['collection'] = self.get_collection()
        return context


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(collection__owner=self.request.user)


class DocumentProcessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            Document,
            pk=pk,
            collection__owner=request.user,
        )
        processed_document = process_document(document)
        return Response(DocumentSerializer(processed_document).data)


class DocumentChunkListView(generics.ListAPIView):
    serializer_class = DocumentChunkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        document = generics.get_object_or_404(
            Document,
            pk=self.kwargs['pk'],
            collection__owner=self.request.user,
        )
        return document.chunks.all()
