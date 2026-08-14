import re
from urllib.parse import parse_qs, urlparse

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
    """Gibt die Kennung zurück, wenn sie elf gültige Zeichen hat."""
    return value if VIDEO_ID_PATTERN.match(value or '') else None


def id_from_query(query):
    """Holt die Kennung aus dem Parameter v einer Adresse."""
    values = parse_qs(query).get('v', [])
    return valid_video_id(values[0]) if values else None


def id_from_path(path):
    """Holt die Kennung aus Pfaden wie shorts, live oder embed."""
    segments = [segment for segment in path.split('/') if segment]
    if len(segments) != 2 or segments[0] not in PATH_PREFIXES:
        return None
    return valid_video_id(segments[1])


def extract_video_id(url):
    """Liest die Kennung des Videos aus einer beliebigen Youtube Adresse."""
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
    """Prüft, ob die Adresse auf ein Youtube Video zeigt."""
    return extract_video_id(url) is not None


def normalize_youtube_url(url):
    """Bringt eine Youtube Adresse in die vom Frontend erwartete Form."""
    return WATCH_URL.format(extract_video_id(url))


def generate_quiz_data(video_url):
    """Liefert Titel, Beschreibung und Fragen zu einem Video.

    Platzhalter, bis die Anbindung an Whisper und Gemini folgt.
    """
    return {
        'title': 'Quiz in Vorbereitung',
        'description': f'Automatisch erzeugtes Quiz zu {video_url}',
        'questions': [],
    }


def save_questions(quiz, questions):
    """Speichert die erzeugten Fragen zu einem Quiz."""
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
    """Erzeugt ein Quiz samt Fragen zu einer Videoadresse."""
    data = generate_quiz_data(video_url)
    quiz = Quiz.objects.create(
        owner=owner,
        video_url=video_url,
        title=data['title'],
        description=data['description'],
    )
    save_questions(quiz, data['questions'])
    return quiz
