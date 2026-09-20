from django.db import connection
from django.db.utils import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok', 'service': 'academic-research-assistant-api'})


@api_view(['GET'])
def database_health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            vector_enabled = cursor.fetchone()[0]
    except DatabaseError:
        return Response(
            {'status': 'error', 'database': 'unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if not vector_enabled:
        return Response(
            {'status': 'error', 'database': 'available', 'pgvector': 'unavailable'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({'status': 'ok', 'database': 'available', 'pgvector': 'available'})
