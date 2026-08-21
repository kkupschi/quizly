from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Question, Quiz
from .utils import is_youtube_url, normalize_youtube_url

User = get_user_model()
PASSWORD = 'Test1234'
VIDEO_ID = 'dQw4w9WgXcQ'
VIDEO_URL = f'https://www.youtube.com/watch?v={VIDEO_ID}'


def logged_in_client(username):
    """Legt einen Benutzer an und gibt einen angemeldeten Client zurück."""
    user = User.objects.create_user(
        username, f'{username}@example.com', PASSWORD
    )
    client = APIClient()
    client.post(
        reverse('login'),
        {'username': username, 'password': PASSWORD},
        format='json',
    )
    return user, client


def make_quiz(owner, title='Testquiz'):
    """Legt ein Quiz mit einer Frage für den Benutzer an."""
    quiz = Quiz.objects.create(
        owner=owner,
        title=title,
        description='Beschreibung',
        video_url=VIDEO_URL,
    )
    Question.objects.create(
        quiz=quiz,
        question_title='Was ist 2 plus 2?',
        question_options=['3', '4', '5', '6'],
        answer='4',
    )
    return quiz


class YoutubeUrlTests(SimpleTestCase):
    """Prüft das Erkennen und Vereinheitlichen der Videoadressen."""

    def test_accepts_common_formats(self):
        """Alle gängigen Youtube Formate werden erkannt."""
        formats = [
            f'https://www.youtube.com/watch?v={VIDEO_ID}',
            f'https://m.youtube.com/watch?v={VIDEO_ID}&t=42s',
            f'https://youtu.be/{VIDEO_ID}?si=abcdefgh',
            f'https://www.youtube.com/shorts/{VIDEO_ID}',
            f'https://www.youtube.com/live/{VIDEO_ID}',
            f'https://www.youtube-nocookie.com/embed/{VIDEO_ID}',
        ]
        for url in formats:
            self.assertTrue(is_youtube_url(url), url)

    def test_normalizes_to_watch_url(self):
        """Jedes Format wird in dieselbe Standardform gebracht."""
        short = normalize_youtube_url(f'https://youtu.be/{VIDEO_ID}')
        shorts = normalize_youtube_url(
            f'https://www.youtube.com/shorts/{VIDEO_ID}'
        )
        self.assertEqual(short, VIDEO_URL)
        self.assertEqual(shorts, VIDEO_URL)

    def test_rejects_foreign_host(self):
        """Ein fremder Host mit passendem Parameter wird abgelehnt."""
        foreign = f'https://boese.example/watch?v={VIDEO_ID}'
        self.assertFalse(is_youtube_url(foreign))
        self.assertFalse(is_youtube_url('https://vimeo.com/12345678'))

    def test_rejects_invalid_video_id(self):
        """Kennungen mit falscher Länge werden abgelehnt."""
        short_id = 'https://www.youtube.com/watch?v=zukurz'
        long_id = 'https://www.youtube.com/watch?v=vielzulangeid123'
        self.assertFalse(is_youtube_url(short_id))
        self.assertFalse(is_youtube_url(long_id))

    def test_rejects_pages_without_video(self):
        """Playlists und Kanalseiten enthalten kein einzelnes Video."""
        playlist = 'https://www.youtube.com/playlist?list=PL1234567890'
        channel = 'https://www.youtube.com/@somechannel'
        self.assertFalse(is_youtube_url(playlist))
        self.assertFalse(is_youtube_url(channel))


class QuizCreateTests(APITestCase):
    """Prüft das Anlegen eines Quiz über eine Videoadresse."""

    def setUp(self):
        """Legt einen angemeldeten Benutzer an."""
        self.url = reverse('quiz-list')
        self.user, self.client = logged_in_client('alice')

    def test_requires_authentication(self):
        """Ohne Anmeldung ist das Anlegen nicht möglich."""
        response = APIClient().post(
            self.url, {'url': VIDEO_URL}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creates_quiz(self):
        """Eine gültige Adresse legt ein Quiz für den Benutzer an."""
        response = self.client.post(
            self.url, {'url': VIDEO_URL}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(Quiz.objects.first().owner, self.user)

    def test_stores_normalized_url(self):
        """Ein Kurzlink wird in der Standardform gespeichert."""
        response = self.client.post(
            self.url, {'url': f'https://youtu.be/{VIDEO_ID}'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['video_url'], VIDEO_URL)

    def test_rejects_foreign_platform(self):
        """Ein Link auf eine andere Plattform wird abgelehnt."""
        response = self.client.post(
            self.url, {'url': 'https://vimeo.com/12345678'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    def test_rejects_broken_url(self):
        """Eine Zeichenkette ohne Adressform wird abgelehnt."""
        response = self.client.post(
            self.url, {'url': 'nichtmaleineurl'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_missing_url(self):
        """Ein Body ohne Adresse wird abgelehnt."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    def test_creates_nothing_on_error(self):
        """Nach einer abgelehnten Anfrage bleibt die Datenbank leer."""
        self.client.post(
            self.url, {'url': 'https://vimeo.com/1'}, format='json'
        )
        self.assertEqual(Quiz.objects.count(), 0)


class QuizListTests(APITestCase):
    """Prüft die Übersicht der eigenen Quizze."""

    def setUp(self):
        """Legt zwei Benutzer mit je einem Quiz an."""
        self.url = reverse('quiz-list')
        self.alice, self.client = logged_in_client('alice')
        self.bob, self.bob_client = logged_in_client('bob')
        make_quiz(self.alice, 'Quiz von Alice')
        make_quiz(self.bob, 'Quiz von Bob')

    def test_requires_authentication(self):
        """Ohne Anmeldung ist die Liste nicht abrufbar."""
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_only_own_quizzes(self):
        """Die Liste enthält keine Quizze anderer Benutzer."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Quiz von Alice')

    def test_includes_questions(self):
        """Jedes Quiz bringt seine Fragen mit."""
        response = self.client.get(self.url)
        questions = response.data[0]['questions']
        self.assertEqual(len(questions), 1)
        options = questions[0]['question_options']
        self.assertEqual(options, ['3', '4', '5', '6'])


class QuizDetailTests(APITestCase):
    """Prüft Abruf, Änderung und Löschung eines einzelnen Quiz."""

    def setUp(self):
        """Legt je ein Quiz für zwei Benutzer an."""
        self.alice, self.client = logged_in_client('alice')
        self.bob, _ = logged_in_client('bob')
        self.own = make_quiz(self.alice, 'Quiz von Alice')
        self.foreign = make_quiz(self.bob, 'Quiz von Bob')
        self.url = reverse('quiz-detail', args=[self.own.id])
        self.foreign_url = reverse('quiz-detail', args=[self.foreign.id])
        self.unknown_url = reverse('quiz-detail', args=[99999])

    def test_requires_authentication(self):
        """Ohne Anmeldung ist der Abruf nicht möglich."""
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_own_quiz(self):
        """Das eigene Quiz wird mit allen Feldern geliefert."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Quiz von Alice')
        self.assertEqual(len(response.data['questions']), 1)

    def test_foreign_quiz_is_forbidden(self):
        """Ein fremdes Quiz führt zu 403, nicht zu 404."""
        response = self.client.get(self.foreign_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_quiz_is_not_found(self):
        """Eine unbekannte Kennung führt zu 404."""
        response = self.client.get(self.unknown_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_title_and_description(self):
        """Titel und Beschreibung lassen sich ändern."""
        payload = {'title': 'Neuer Titel', 'description': 'Neue Beschreibung'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own.refresh_from_db()
        self.assertEqual(self.own.title, 'Neuer Titel')

    def test_patch_ignores_video_url(self):
        """Die Videoadresse lässt sich nicht nachträglich austauschen."""
        payload = {'video_url': 'https://boese.example/x'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own.refresh_from_db()
        self.assertEqual(self.own.video_url, VIDEO_URL)

    def test_patch_on_foreign_quiz_is_forbidden(self):
        """Ein fremdes Quiz lässt sich nicht ändern."""
        response = self.client.patch(
            self.foreign_url, {'title': 'Geklaut'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.title, 'Quiz von Bob')

    def test_put_is_not_allowed(self):
        """Die Dokumentation kennt nur PATCH, deshalb ist PUT gesperrt."""
        response = self.client.put(self.url, {'title': 'X'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_removes_quiz_and_questions(self):
        """Das Löschen entfernt auch alle Fragen des Quiz."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.own.id).exists())
        self.assertFalse(Question.objects.filter(quiz_id=self.own.id).exists())

    def test_delete_on_foreign_quiz_is_forbidden(self):
        """Ein fremdes Quiz lässt sich nicht löschen."""
        response = self.client.delete(self.foreign_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(id=self.foreign.id).exists())

    def test_delete_unknown_quiz_is_not_found(self):
        """Das Löschen einer unbekannten Kennung führt zu 404."""
        response = self.client.delete(self.unknown_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
