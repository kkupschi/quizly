import re

from .models import Question, Quiz

YOUTUBE_PATTERN = re.compile(
    r'^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}'
)


def is_youtube_url(url):
    """Prüft, ob die Adresse auf ein Youtube Video zeigt."""
    return bool(YOUTUBE_PATTERN.match(url))


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
