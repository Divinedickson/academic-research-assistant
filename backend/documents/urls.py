from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (
    CollectionAskView,
    CollectionDocumentListCreateView,
    CollectionSemanticSearchView,
    DocumentChunkListView,
    DocumentDetailView,
    DocumentEmbedView,
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
    path(
        'collections/<int:collection_id>/search/',
        CollectionSemanticSearchView.as_view(),
        name='collection-search',
    ),
    path(
        'collections/<int:collection_id>/ask/',
        CollectionAskView.as_view(),
        name='collection-ask',
    ),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/process/', DocumentProcessView.as_view(), name='document-process'),
    path('documents/<int:pk>/embed/', DocumentEmbedView.as_view(), name='document-embed'),
    path('documents/<int:pk>/chunks/', DocumentChunkListView.as_view(), name='document-chunks'),
    *router.urls,
]
