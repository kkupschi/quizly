from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()
PASSWORD = 'Test1234'


def registration_payload(**overrides):
    """Builds a valid registration body with optional changes."""
    payload = {
        'username': 'alice',
        'email': 'alice@example.com',
        'password': PASSWORD,
        'confirmed_password': PASSWORD,
    }
    payload.update(overrides)
    return payload


def login_user(client, username='alice'):
    """Creates a user and logs it in through the endpoint."""
    user = User.objects.create_user(
        username, f'{username}@example.com', PASSWORD
    )
    client.post(
        reverse('login'),
        {'username': username, 'password': PASSWORD},
        format='json',
    )
    return user


class RegistrationTests(APITestCase):
    """Tests the endpoint that registers new users."""

    def setUp(self):
        """Stores the address of the endpoint."""
        self.url = reverse('register')

    def test_creates_user(self):
        """A valid request creates the user."""
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], 'User created successfully!')
        self.assertTrue(User.objects.filter(username='alice').exists())

    def test_hashes_password(self):
        """The password is never stored in plain text."""
        self.client.post(self.url, registration_payload(), format='json')
        user = User.objects.get(username='alice')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_rejects_duplicate_username(self):
        """A username that is already taken is rejected."""
        User.objects.create_user('alice', 'other@example.com', PASSWORD)
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_rejects_duplicate_email(self):
        """An email address that is already taken is rejected."""
        User.objects.create_user('bob', 'alice@example.com', PASSWORD)
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_rejects_password_mismatch(self):
        """A confirmation that differs from the password is rejected."""
        payload = registration_payload(confirmed_password='Different1234')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_password', response.data)

    def test_rejects_missing_fields(self):
        """An empty body names every missing field."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ['username', 'email', 'password']:
            self.assertIn(field, response.data)

    def test_rejects_get(self):
        """The endpoint accepts POST only."""
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


class LoginTests(APITestCase):
    """Tests the login and the cookies it sets."""

    def setUp(self):
        """Creates a user that can log in."""
        self.url = reverse('login')
        self.user = User.objects.create_user(
            'alice', 'alice@example.com', PASSWORD
        )

    def login(self, **overrides):
        """Sends a login request with optionally changed data."""
        payload = {'username': 'alice', 'password': PASSWORD}
        payload.update(overrides)
        return self.client.post(self.url, payload, format='json')

    def test_sets_both_cookies(self):
        """A valid login sets both tokens as cookies."""
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_cookies_are_http_only(self):
        """The cookies cannot be read by JavaScript."""
        response = self.login()
        for name in ['access_token', 'refresh_token']:
            self.assertTrue(response.cookies[name]['httponly'])

    def test_returns_user_data(self):
        """The response contains the data of the user that logged in."""
        response = self.login()
        self.assertEqual(response.data['detail'], 'Login successfully!')
        self.assertEqual(response.data['user']['username'], 'alice')
        self.assertEqual(response.data['user']['id'], self.user.id)

    def test_response_contains_no_token(self):
        """The tokens live in the cookies only, never in the body."""
        response = self.login()
        body = str(response.data)
        self.assertNotIn('access', body)
        self.assertNotIn('refresh', body)

    def test_rejects_wrong_password(self):
        """A wrong password leads to 401."""
        response = self.login(password='Wrong1234')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access_token', response.cookies)

    def test_rejects_unknown_user(self):
        """An unknown username leads to 401."""
        response = self.login(username='nobody')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_error_message_is_generic(self):
        """The error message does not tell which field was wrong."""
        wrong_user = self.login(username='nobody')
        wrong_password = self.login(password='Wrong1234')
        self.assertEqual(
            wrong_user.data['detail'], wrong_password.data['detail']
        )

    def test_rejects_empty_body(self):
        """An empty body leads to 401 instead of a server error."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    """Tests the logout and the blacklisting of the token."""

    def setUp(self):
        """Creates a user that is logged in."""
        self.url = reverse('logout')
        login_user(self.client)

    def test_requires_authentication(self):
        """Without a login the logout is not possible."""
        self.client.cookies.clear()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_expected_detail(self):
        """The response matches the text from the documentation."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Log-Out successfully!', response.data['detail'])

    def test_clears_cookies(self):
        """Both cookies are cleared in the browser."""
        response = self.client.post(self.url)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')

    def test_blacklists_refresh_token(self):
        """After the logout the token cannot be refreshed any more."""
        self.client.post(self.url)
        response = self.client.post(reverse('token-refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTests(APITestCase):
    """Tests the renewal of the access token."""

    def setUp(self):
        """Creates a user that is logged in."""
        self.url = reverse('token-refresh')
        login_user(self.client)

    def test_sets_new_access_cookie(self):
        """A valid token returns a new access token."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access_token', response.cookies)

    def test_rejects_missing_cookie(self):
        """Without a cookie the renewal is rejected."""
        self.client.cookies.clear()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_invalid_cookie(self):
        """A manipulated token is rejected."""
        self.client.cookies['refresh_token'] = 'not.even.a.jwt'
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
