from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('api-health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

# Create your tests here.
