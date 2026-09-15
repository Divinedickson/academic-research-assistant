from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import Document, ResearchCollection
from .serializers import DocumentSerializer, ResearchCollectionSerializer


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
