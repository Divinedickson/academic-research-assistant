from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.refresh_url = reverse('token-refresh')
        self.me_url = reverse('auth-me')
        self.password = 'ResearchPass123!'

    def test_registration_creates_user_and_returns_tokens(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'ada',
                'email': 'ada@example.com',
                'password': self.password,
                'password_confirmation': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'ada')
        self.assertNotIn('password', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.filter(username='ada').exists())

    def test_login_returns_tokens_for_valid_credentials(self):
        User.objects.create_user(
            username='grace',
            email='grace@example.com',
            password=self.password,
        )

        response = self.client.post(
            self.login_url,
            {'username': 'grace', 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'grace')
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_refresh_returns_new_access_token(self):
        register_response = self.client.post(
            self.register_url,
            {
                'username': 'katherine',
                'email': 'katherine@example.com',
                'password': self.password,
                'password_confirmation': self.password,
            },
            format='json',
        )

        response = self.client.post(
            self.refresh_url,
            {'refresh': register_response.data['refresh']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(
            username='dorothy',
            email='dorothy@example.com',
            password=self.password,
        )

        response = self.client.post(
            self.login_url,
            {'username': 'dorothy', 'password': 'WrongPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(
            username='mary',
            email='mary@example.com',
            password=self.password,
        )

        response = self.client.post(
            self.register_url,
            {
                'username': 'mary',
                'email': 'mary2@example.com',
                'password': self.password,
                'password_confirmation': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            self.register_url,
            {
                'username': 'rosalind',
                'email': 'rosalind@example.com',
                'password': self.password,
                'password_confirmation': 'DifferentPass123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirmation', response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        user = User.objects.create_user(
            username='hedy',
            email='hedy@example.com',
            password=self.password,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'hedy')
