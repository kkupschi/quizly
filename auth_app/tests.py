from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()
PASSWORD = 'Test1234'


def registration_payload(**overrides):
    """Baut einen gültigen Registrierungsbody mit optionalen Änderungen."""
    payload = {
        'username': 'alice',
        'email': 'alice@example.com',
        'password': PASSWORD,
        'confirmed_password': PASSWORD,
    }
    payload.update(overrides)
    return payload


def login_user(client, username='alice'):
    """Legt einen Benutzer an und meldet ihn über den Endpunkt an."""
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
    """Prüft den Endpunkt zur Registrierung neuer Benutzer."""

    def setUp(self):
        """Merkt sich die Adresse des Endpunkts."""
        self.url = reverse('register')

    def test_creates_user(self):
        """Eine gültige Anfrage legt den Benutzer an."""
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], 'User created successfully!')
        self.assertTrue(User.objects.filter(username='alice').exists())

    def test_hashes_password(self):
        """Das Passwort wird niemals im Klartext gespeichert."""
        self.client.post(self.url, registration_payload(), format='json')
        user = User.objects.get(username='alice')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_rejects_duplicate_username(self):
        """Ein bereits vergebener Benutzername wird abgelehnt."""
        User.objects.create_user('alice', 'other@example.com', PASSWORD)
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_rejects_duplicate_email(self):
        """Eine bereits vergebene Mailadresse wird abgelehnt."""
        User.objects.create_user('bob', 'alice@example.com', PASSWORD)
        response = self.client.post(
            self.url, registration_payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_rejects_password_mismatch(self):
        """Abweichende Passwortbestätigung wird abgelehnt."""
        payload = registration_payload(confirmed_password='Anders1234')
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_password', response.data)

    def test_rejects_missing_fields(self):
        """Ein leerer Body nennt alle fehlenden Felder."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ['username', 'email', 'password']:
            self.assertIn(field, response.data)

    def test_rejects_get(self):
        """Der Endpunkt nimmt ausschließlich POST entgegen."""
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


class LoginTests(APITestCase):
    """Prüft die Anmeldung und das Setzen der Cookies."""

    def setUp(self):
        """Legt einen Benutzer für die Anmeldung an."""
        self.url = reverse('login')
        self.user = User.objects.create_user(
            'alice', 'alice@example.com', PASSWORD
        )

    def login(self, **overrides):
        """Sendet eine Anmeldung mit optional geänderten Daten."""
        payload = {'username': 'alice', 'password': PASSWORD}
        payload.update(overrides)
        return self.client.post(self.url, payload, format='json')

    def test_sets_both_cookies(self):
        """Eine gültige Anmeldung setzt beide Token als Cookies."""
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)

    def test_cookies_are_http_only(self):
        """Die Cookies sind für JavaScript nicht lesbar."""
        response = self.login()
        for name in ['access_token', 'refresh_token']:
            self.assertTrue(response.cookies[name]['httponly'])

    def test_returns_user_data(self):
        """Die Antwort enthält die Daten des angemeldeten Benutzers."""
        response = self.login()
        self.assertEqual(response.data['detail'], 'Login successfully!')
        self.assertEqual(response.data['user']['username'], 'alice')
        self.assertEqual(response.data['user']['id'], self.user.id)

    def test_response_contains_no_token(self):
        """Die Token stehen nur im Cookie, niemals im Antwortkörper."""
        response = self.login()
        body = str(response.data)
        self.assertNotIn('access', body)
        self.assertNotIn('refresh', body)

    def test_rejects_wrong_password(self):
        """Ein falsches Passwort führt zu 401."""
        response = self.login(password='Falsch1234')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access_token', response.cookies)

    def test_rejects_unknown_user(self):
        """Ein unbekannter Benutzername führt zu 401."""
        response = self.login(username='niemand')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_error_message_is_generic(self):
        """Die Fehlermeldung verrät nicht, welches Feld falsch war."""
        wrong_user = self.login(username='niemand')
        wrong_password = self.login(password='Falsch1234')
        self.assertEqual(
            wrong_user.data['detail'], wrong_password.data['detail']
        )

    def test_rejects_empty_body(self):
        """Ein leerer Body führt zu 401 statt zu einem Serverfehler."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    """Prüft die Abmeldung und das Sperren der Token."""

    def setUp(self):
        """Legt einen angemeldeten Benutzer an."""
        self.url = reverse('logout')
        login_user(self.client)

    def test_requires_authentication(self):
        """Ohne Anmeldung ist die Abmeldung nicht möglich."""
        self.client.cookies.clear()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_expected_detail(self):
        """Die Antwort entspricht dem Text aus der Dokumentation."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Log-Out successfully!', response.data['detail'])

    def test_clears_cookies(self):
        """Beide Cookies werden im Browser geleert."""
        response = self.client.post(self.url)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')

    def test_blacklists_refresh_token(self):
        """Der Token lässt sich nach der Abmeldung nicht mehr erneuern."""
        self.client.post(self.url)
        response = self.client.post(reverse('token-refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTests(APITestCase):
    """Prüft das Erneuern des Zugriffstokens."""

    def setUp(self):
        """Legt einen angemeldeten Benutzer an."""
        self.url = reverse('token-refresh')
        login_user(self.client)

    def test_sets_new_access_cookie(self):
        """Ein gültiger Token liefert einen neuen Zugriffstoken."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access_token', response.cookies)

    def test_rejects_missing_cookie(self):
        """Ohne Cookie wird die Erneuerung abgelehnt."""
        self.client.cookies.clear()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_invalid_cookie(self):
        """Ein manipulierter Token wird abgelehnt."""
        self.client.cookies['refresh_token'] = 'nichteinmalein.jwt.token'
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
