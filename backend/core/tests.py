from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('api-health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_database_health_check_returns_ok(self):
        response = self.client.get(reverse('api-database-health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['database'], 'available')
        self.assertEqual(response.json()['pgvector'], 'available')

    def test_database_health_check_returns_safe_unavailable_response(self):
        with patch('core.views.connection.cursor', side_effect=DatabaseError('connection details')):
            response = self.client.get(reverse('api-database-health'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'error', 'database': 'unavailable'})
        self.assertNotContains(response, 'connection details', status_code=503)
