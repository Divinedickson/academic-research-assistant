from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CollectionDocumentListCreateView,
    DocumentChunkListView,
    DocumentDetailView,
    DocumentProcessView,
    ResearchCollectionViewSet,
)


router = SimpleRouter()
router.register('collections', ResearchCollectionViewSet, basename='collection')

urlpatterns = [
    path(
        'collections/<int:collection_id>/documents/',
        CollectionDocumentListCreateView.as_view(),
        name='collection-documents',
    ),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/process/', DocumentProcessView.as_view(), name='document-process'),
    path('documents/<int:pk>/chunks/', DocumentChunkListView.as_view(), name='document-chunks'),
    *router.urls,
]
