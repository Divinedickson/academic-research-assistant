from django.db.models import Count
from rest_framework import generics, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, ResearchCollection
from .serializers import (
    DocumentChunkSerializer,
    DocumentSerializer,
    ResearchCollectionSerializer,
    SemanticSearchRequestSerializer,
)
from .services import EmbeddingError, embed_document, process_document, semantic_search_collection


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


class DocumentEmbedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            Document,
            pk=pk,
            collection__owner=request.user,
        )

        try:
            embedded_document = embed_document(document)
        except EmbeddingError as exc:
            return Response({'detail': str(exc)}, status=400)

        return Response(DocumentSerializer(embedded_document).data)


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


class CollectionSemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, collection_id):
        collection = generics.get_object_or_404(
            ResearchCollection,
            id=collection_id,
            owner=request.user,
        )
        serializer = SemanticSearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = semantic_search_collection(
            collection,
            query=serializer.validated_data['query'],
            top_k=serializer.validated_data['top_k'],
        )

        return Response(
            {
                'query': serializer.validated_data['query'],
                'top_k': serializer.validated_data['top_k'],
                'score_description': (
                    'similarity_score is cosine similarity in the range -1 to 1; '
                    'higher is more similar. cosine_distance is 1 - similarity, where lower is closer.'
                ),
                'results': [result.__dict__ for result in results],
            },
        )
