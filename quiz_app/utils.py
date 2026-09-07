import re
from urllib.parse import parse_qs, urlparse

from .functions import generate_quiz_data
from .models import Question, Quiz

VIDEO_ID_PATTERN = re.compile(r'^[\w-]{11}$')
WATCH_URL = 'https://www.youtube.com/watch?v={}'
ALLOWED_SCHEMES = ('http', 'https')
SHORT_HOSTS = ('youtu.be', 'www.youtu.be')
YOUTUBE_HOSTS = (
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtube-nocookie.com',
    'www.youtube-nocookie.com',
)
PATH_PREFIXES = ('watch', 'embed', 'shorts', 'live', 'v', 'e')


def valid_video_id(value):
    """Returns the video id if it consists of eleven valid characters."""
    return value if VIDEO_ID_PATTERN.match(value or '') else None


def id_from_query(query):
    """Reads the video id from the v parameter of an address."""
    values = parse_qs(query).get('v', [])
    return valid_video_id(values[0]) if values else None


def id_from_path(path):
    """Reads the video id from paths such as shorts, live or embed."""
    segments = [segment for segment in path.split('/') if segment]
    if len(segments) != 2 or segments[0] not in PATH_PREFIXES:
        return None
    return valid_video_id(segments[1])


def extract_video_id(url):
    """Reads the video id from any supported Youtube address."""
    parts = urlparse(url)
    host = parts.netloc.lower()
    if parts.scheme not in ALLOWED_SCHEMES:
        return None
    if host in SHORT_HOSTS:
        return valid_video_id(parts.path.lstrip('/'))
    if host not in YOUTUBE_HOSTS:
        return None
    return id_from_query(parts.query) or id_from_path(parts.path)


def is_youtube_url(url):
    """Checks whether the address points to a Youtube video."""
    return extract_video_id(url) is not None


def normalize_youtube_url(url):
    """Converts a Youtube address into the form the frontend expects."""
    return WATCH_URL.format(extract_video_id(url))


def save_questions(quiz, questions):
    """Stores the generated questions of a quiz."""
    Question.objects.bulk_create([
        Question(
            quiz=quiz,
            question_title=item['question_title'],
            question_options=item['question_options'],
            answer=item['answer'],
        )
        for item in questions
    ])


def create_quiz_from_url(owner, video_url):
    """Creates a quiz together with its questions for a video address."""
    data = generate_quiz_data(video_url)
    quiz = Quiz.objects.create(
        owner=owner,
        video_url=video_url,
        title=data['title'],
        description=data['description'],
    )
    save_questions(quiz, data['questions'])
    return quiz
