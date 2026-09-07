import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from google.genai import errors as genai_errors
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .functions import QuizGenerationError, ask_gemini, parse_quiz, run_whisper
from .models import Question, Quiz
from .utils import is_youtube_url, normalize_youtube_url

User = get_user_model()
PASSWORD = 'Test1234'
VIDEO_ID = 'dQw4w9WgXcQ'
VIDEO_URL = f'https://www.youtube.com/watch?v={VIDEO_ID}'


def logged_in_client(username):
    """Creates a user and returns a client that is logged in."""
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


def fake_quiz_data(count=10):
    """Builds a valid answer as the AI would deliver it."""
    return {
        'title': 'Generated quiz',
        'description': 'Description from the AI',
        'questions': [
            {
                'question_title': f'Question {number}',
                'question_options': ['A', 'B', 'C', 'D'],
                'answer': 'B',
            }
            for number in range(1, count + 1)
        ],
    }


def make_quiz(owner, title='Test quiz'):
    """Creates a quiz with one question for the given user."""
    quiz = Quiz.objects.create(
        owner=owner,
        title=title,
        description='Description',
        video_url=VIDEO_URL,
    )
    Question.objects.create(
        quiz=quiz,
        question_title='What is 2 plus 2?',
        question_options=['3', '4', '5', '6'],
        answer='4',
    )
    return quiz


class YoutubeUrlTests(SimpleTestCase):
    """Tests how video addresses are recognized and normalized."""

    def test_accepts_common_formats(self):
        """Every common Youtube format is recognized."""
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
        """Every format ends up in the same standard form."""
        short = normalize_youtube_url(f'https://youtu.be/{VIDEO_ID}')
        shorts = normalize_youtube_url(
            f'https://www.youtube.com/shorts/{VIDEO_ID}'
        )
        self.assertEqual(short, VIDEO_URL)
        self.assertEqual(shorts, VIDEO_URL)

    def test_rejects_foreign_host(self):
        """A foreign host with a matching parameter is rejected."""
        foreign = f'https://evil.example/watch?v={VIDEO_ID}'
        self.assertFalse(is_youtube_url(foreign))
        self.assertFalse(is_youtube_url('https://vimeo.com/12345678'))

    def test_rejects_invalid_video_id(self):
        """Video ids with a wrong length are rejected."""
        short_id = 'https://www.youtube.com/watch?v=tooshort'
        long_id = 'https://www.youtube.com/watch?v=waytoolongvideoid123'
        self.assertFalse(is_youtube_url(short_id))
        self.assertFalse(is_youtube_url(long_id))

    def test_rejects_pages_without_video(self):
        """Playlists and channel pages contain no single video."""
        playlist = 'https://www.youtube.com/playlist?list=PL1234567890'
        channel = 'https://www.youtube.com/@somechannel'
        self.assertFalse(is_youtube_url(playlist))
        self.assertFalse(is_youtube_url(channel))


class QuizCreateTests(APITestCase):
    """Tests the creation of a quiz from a video address."""

    def setUp(self):
        """Creates a user that is logged in."""
        self.url = reverse('quiz-list')
        self.user, self.client = logged_in_client('alice')
        patcher = mock.patch(
            'quiz_app.utils.generate_quiz_data',
            return_value=fake_quiz_data(),
        )
        self.addCleanup(patcher.stop)
        self.generate = patcher.start()

    def test_requires_authentication(self):
        """Without a login the creation is not possible."""
        response = APIClient().post(
            self.url, {'url': VIDEO_URL}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creates_quiz(self):
        """A valid address creates a quiz for the user."""
        response = self.client.post(
            self.url, {'url': VIDEO_URL}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(Quiz.objects.first().owner, self.user)

    def test_stores_normalized_url(self):
        """A short link is stored in the standard form."""
        response = self.client.post(
            self.url, {'url': f'https://youtu.be/{VIDEO_ID}'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['video_url'], VIDEO_URL)

    def test_rejects_foreign_platform(self):
        """A link to another platform is rejected."""
        response = self.client.post(
            self.url, {'url': 'https://vimeo.com/12345678'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    def test_rejects_broken_url(self):
        """A string without the form of an address is rejected."""
        response = self.client.post(
            self.url, {'url': 'noturlatall'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_missing_url(self):
        """A body without an address is rejected."""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)

    def test_creates_nothing_on_error(self):
        """After a rejected request the database stays empty."""
        self.client.post(
            self.url, {'url': 'https://vimeo.com/1'}, format='json'
        )
        self.assertEqual(Quiz.objects.count(), 0)


class QuizListTests(APITestCase):
    """Tests the overview of the own quizzes."""

    def setUp(self):
        """Creates two users with one quiz each."""
        self.url = reverse('quiz-list')
        self.alice, self.client = logged_in_client('alice')
        self.bob, self.bob_client = logged_in_client('bob')
        make_quiz(self.alice, 'Quiz of Alice')
        make_quiz(self.bob, 'Quiz of Bob')

    def test_requires_authentication(self):
        """Without a login the list cannot be read."""
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_only_own_quizzes(self):
        """The list contains no quizzes of other users."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Quiz of Alice')

    def test_includes_questions(self):
        """Every quiz brings its questions along."""
        response = self.client.get(self.url)
        questions = response.data[0]['questions']
        self.assertEqual(len(questions), 1)
        options = questions[0]['question_options']
        self.assertEqual(options, ['3', '4', '5', '6'])


class QuizDetailTests(APITestCase):
    """Tests reading, updating and deleting a single quiz."""

    def setUp(self):
        """Creates one quiz for each of two users."""
        self.alice, self.client = logged_in_client('alice')
        self.bob, _ = logged_in_client('bob')
        self.own = make_quiz(self.alice, 'Quiz of Alice')
        self.foreign = make_quiz(self.bob, 'Quiz of Bob')
        self.url = reverse('quiz-detail', args=[self.own.id])
        self.foreign_url = reverse('quiz-detail', args=[self.foreign.id])
        self.unknown_url = reverse('quiz-detail', args=[99999])

    def test_requires_authentication(self):
        """Without a login the quiz cannot be read."""
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_own_quiz(self):
        """The own quiz is returned with all of its fields."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Quiz of Alice')
        self.assertEqual(len(response.data['questions']), 1)

    def test_foreign_quiz_is_forbidden(self):
        """A quiz of another user leads to 403 and not to 404."""
        response = self.client.get(self.foreign_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_quiz_is_not_found(self):
        """An unknown id leads to 404."""
        response = self.client.get(self.unknown_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_updates_title_and_description(self):
        """Title and description can be changed."""
        payload = {'title': 'New title', 'description': 'New description'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own.refresh_from_db()
        self.assertEqual(self.own.title, 'New title')

    def test_patch_ignores_video_url(self):
        """The video address cannot be exchanged afterwards."""
        payload = {'video_url': 'https://evil.example/x'}
        response = self.client.patch(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own.refresh_from_db()
        self.assertEqual(self.own.video_url, VIDEO_URL)

    def test_patch_on_foreign_quiz_is_forbidden(self):
        """A quiz of another user cannot be changed."""
        response = self.client.patch(
            self.foreign_url, {'title': 'Stolen'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.title, 'Quiz of Bob')

    def test_put_is_not_allowed(self):
        """The documentation knows PATCH only, so PUT is blocked."""
        response = self.client.put(self.url, {'title': 'X'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_removes_quiz_and_questions(self):
        """Deleting a quiz removes all of its questions as well."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.own.id).exists())
        self.assertFalse(Question.objects.filter(quiz_id=self.own.id).exists())

    def test_delete_on_foreign_quiz_is_forbidden(self):
        """A quiz of another user cannot be deleted."""
        response = self.client.delete(self.foreign_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(id=self.foreign.id).exists())

    def test_delete_unknown_quiz_is_not_found(self):
        """Deleting an unknown id leads to 404."""
        response = self.client.delete(self.unknown_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class QuizGenerationParsingTests(SimpleTestCase):
    """Tests how the answer of the AI is read and validated."""

    def test_parses_valid_answer(self):
        """A correct answer is accepted."""
        data = parse_quiz(json.dumps(fake_quiz_data()))
        self.assertEqual(data['title'], 'Generated quiz')
        self.assertEqual(len(data['questions']), 10)

    def test_accepts_code_fence(self):
        """An answer wrapped in backticks is still read."""
        raw = '```json\n' + json.dumps(fake_quiz_data()) + '\n```'
        data = parse_quiz(raw)
        self.assertEqual(len(data['questions']), 10)

    def test_rejects_broken_json(self):
        """A broken answer leads to a clear error."""
        with self.assertRaises(QuizGenerationError):
            parse_quiz('this is not json')

    def test_rejects_missing_questions(self):
        """An answer without questions is rejected."""
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps({'title': 'X', 'description': 'Y'}))

    def test_rejects_empty_questions(self):
        """An empty list of questions is rejected."""
        data = fake_quiz_data(0)
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))

    def test_rejects_wrong_question_count(self):
        """An answer with fewer than ten questions is rejected."""
        data = fake_quiz_data(5)
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))

    def test_rejects_wrong_option_count(self):
        """A question with three options is rejected."""
        data = fake_quiz_data()
        data['questions'][0]['question_options'] = ['A', 'B', 'C']
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))

    def test_rejects_answer_outside_options(self):
        """An answer that is not among the options is rejected."""
        data = fake_quiz_data()
        data['questions'][0]['answer'] = 'Z'
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))

    def test_rejects_question_without_text(self):
        """A question without text is rejected."""
        data = fake_quiz_data()
        data['questions'][0]['question_title'] = ''
        with self.assertRaises(QuizGenerationError):
            parse_quiz(json.dumps(data))


class TranscriptionTests(SimpleTestCase):
    """Tests how failures of Whisper are reported."""

    @mock.patch('quiz_app.functions.whisper.load_model')
    def test_reports_missing_ffmpeg(self, load_model):
        """A missing FFmpeg leads to a readable error instead of a crash."""
        load_model.side_effect = RuntimeError('ffmpeg not found')
        with self.assertRaises(QuizGenerationError) as caught:
            run_whisper('audio.mp3')
        self.assertIn('FFmpeg', str(caught.exception))


@override_settings(
    GEMINI_API_KEY='testkey',
    GEMINI_MODEL='primary',
    GEMINI_FALLBACK_MODELS=['fallback'],
)
class GeminiModelTests(SimpleTestCase):
    """Tests which models are asked and how failures are handled."""

    def api_error(self):
        """Builds the error the AI raises when a model is unavailable."""
        return genai_errors.APIError(
            503, {'error': {'message': 'model is overloaded'}}
        )

    def client_mock(self, side_effect):
        """Builds a client whose generate_content behaves as given."""
        client = mock.Mock()
        client.models.generate_content.side_effect = side_effect
        return client

    def used_models(self, client):
        """Returns the model names the client was called with."""
        return [
            call.kwargs['model']
            for call in client.models.generate_content.call_args_list
        ]

    def test_uses_configured_model_first(self):
        """The model from the settings is asked before any fallback."""
        client = self.client_mock([mock.Mock(text='answer')])
        with mock.patch('quiz_app.functions.genai.Client',
                        return_value=client):
            self.assertEqual(ask_gemini('prompt'), 'answer')
        self.assertEqual(self.used_models(client), ['primary'])

    def test_falls_back_to_next_model(self):
        """An unavailable model is replaced by the next one."""
        client = self.client_mock(
            [self.api_error(), mock.Mock(text='answer')]
        )
        with mock.patch('quiz_app.functions.genai.Client',
                        return_value=client):
            self.assertEqual(ask_gemini('prompt'), 'answer')
        self.assertEqual(self.used_models(client), ['primary', 'fallback'])

    def test_reports_error_when_all_models_fail(self):
        """If every model fails the user gets a hint instead of a 500."""
        client = self.client_mock([self.api_error(), self.api_error()])
        with mock.patch('quiz_app.functions.genai.Client',
                        return_value=client):
            with self.assertRaises(QuizGenerationError) as caught:
                ask_gemini('prompt')
        self.assertIn('GEMINI_MODEL', str(caught.exception))

    @override_settings(GEMINI_API_KEY='')
    def test_requires_api_key(self):
        """Without an API key the generation stops right away."""
        with self.assertRaises(QuizGenerationError):
            ask_gemini('prompt')


class QuizGenerationEndpointTests(APITestCase):
    """Tests how endpoint and generation work together."""

    def setUp(self):
        """Creates a user that is logged in."""
        self.url = reverse('quiz-list')
        self.user, self.client = logged_in_client('alice')

    def post_video(self):
        """Sends a valid video address to the endpoint."""
        return self.client.post(self.url, {'url': VIDEO_URL}, format='json')

    @mock.patch('quiz_app.utils.generate_quiz_data')
    def test_saves_all_questions(self, generate):
        """Every delivered question ends up in the database."""
        generate.return_value = fake_quiz_data()
        response = self.post_video()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Question.objects.count(), 10)

    @mock.patch('quiz_app.utils.generate_quiz_data')
    def test_uses_title_from_ai(self, generate):
        """Title and description come from the answer of the AI."""
        generate.return_value = fake_quiz_data(1)
        response = self.post_video()
        self.assertEqual(response.data['title'], 'Generated quiz')
        self.assertEqual(
            response.data['description'], 'Description from the AI'
        )

    @mock.patch('quiz_app.utils.generate_quiz_data')
    def test_reports_generation_failure(self, generate):
        """A failure during the generation leads to 400 with an explanation."""
        generate.side_effect = QuizGenerationError('Video not available.')
        response = self.post_video()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Video not available.')

    @mock.patch('quiz_app.utils.generate_quiz_data')
    def test_saves_nothing_on_failure(self, generate):
        """After a failure no half quiz is left behind."""
        generate.side_effect = QuizGenerationError('Generation failed.')
        self.post_video()
        self.assertEqual(Quiz.objects.count(), 0)
