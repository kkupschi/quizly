import json
import os
import tempfile

import whisper
import yt_dlp
from django.conf import settings
from google import genai

GEMINI_MODEL = 'gemini-flash-latest'
WHISPER_MODEL = 'base'
QUESTION_COUNT = 10
OPTION_COUNT = 4
AUDIO_NAME = 'audio'
RESPONSE_CONFIG = {'response_mime_type': 'application/json'}

PROMPT = """Du bist ein Werkzeug, das aus einem Transkript ein Quiz erstellt.

Erstelle genau {count} Fragen zum folgenden Inhalt. Jede Frage hat genau
{options} Antwortmöglichkeiten, von denen genau eine richtig ist. Die
richtige Antwort muss wortgleich in den Antwortmöglichkeiten vorkommen.

Antworte ausschließlich mit JSON in dieser Struktur:
{{
  "title": "kurzer Titel des Quiz",
  "description": "ein bis zwei Sätze zum Inhalt",
  "questions": [
    {{
      "question_title": "die Frage",
      "question_options": ["A", "B", "C", "D"],
      "answer": "A"
    }}
  ]
}}

Verwende dieselbe Sprache wie das Transkript.

Transkript:
{transcript}
"""


class QuizGenerationError(Exception):
    """Fehler, der beim Erzeugen eines Quiz auftreten kann."""


def download_audio(video_url, target_dir):
    """Lädt die Tonspur eines Videos und gibt den Dateipfad zurück."""
    options = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(target_dir, f'{AUDIO_NAME}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True,
        'noprogress': True,
    }
    return run_download(video_url, options, target_dir)


def run_download(video_url, options, target_dir):
    """Führt den Download aus und meldet Fehler verständlich zurück."""
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([video_url])
    except yt_dlp.utils.DownloadError as error:
        raise QuizGenerationError(
            'Das Video konnte nicht geladen werden.'
        ) from error
    return os.path.join(target_dir, f'{AUDIO_NAME}.mp3')


def transcribe_audio(audio_path):
    """Wandelt eine Audiodatei mit Whisper in Text um."""
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(audio_path)
    transcript = result['text'].strip()
    if not transcript:
        raise QuizGenerationError(
            'Das Video enthält keine gesprochene Sprache.'
        )
    return transcript


def build_prompt(transcript):
    """Baut die Anweisung für die KI aus dem Transkript."""
    return PROMPT.format(
        count=QUESTION_COUNT,
        options=OPTION_COUNT,
        transcript=transcript,
    )


def ask_gemini(prompt):
    """Schickt die Anweisung an Gemini und gibt den Antworttext zurück."""
    if not settings.GEMINI_API_KEY:
        raise QuizGenerationError('Es ist kein Zugang zur KI hinterlegt.')
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=RESPONSE_CONFIG,
    )
    return response.text


def strip_code_fence(text):
    """Entfernt eine mögliche Umrandung aus Gegenstrichen um das JSON."""
    cleaned = (text or '').strip()
    if not cleaned.startswith('```'):
        return cleaned
    cleaned = cleaned.split('\n', 1)[-1]
    return cleaned.rsplit('```', 1)[0].strip()


def validate_question(question):
    """Prüft eine einzelne Frage auf Vollständigkeit."""
    options = question.get('question_options')
    if not question.get('question_title'):
        raise QuizGenerationError('Eine Frage der KI hat keinen Text.')
    if not isinstance(options, list) or len(options) != OPTION_COUNT:
        raise QuizGenerationError(
            f'Eine Frage hat nicht {OPTION_COUNT} Antwortmöglichkeiten.'
        )
    if question.get('answer') not in options:
        raise QuizGenerationError(
            'Die richtige Antwort fehlt in den Optionen.'
        )


def validate_quiz(data):
    """Prüft, ob die Antwort der KI die erwartete Struktur hat."""
    fragen = data.get('questions') if isinstance(data, dict) else None
    if not isinstance(fragen, list):
        raise QuizGenerationError('Die Antwort der KI enthält kein Quiz.')
    if not fragen:
        raise QuizGenerationError('Die KI hat keine Fragen geliefert.')
    for question in fragen:
        validate_question(question)


def parse_quiz(raw_text):
    """Liest das Quiz aus der Antwort der KI und prüft es."""
    try:
        data = json.loads(strip_code_fence(raw_text))
    except json.JSONDecodeError as error:
        raise QuizGenerationError(
            'Die Antwort der KI war kein gültiges JSON.'
        ) from error
    validate_quiz(data)
    return data


def generate_quiz_data(video_url):
    """Erzeugt Titel, Beschreibung und Fragen zu einem Video."""
    with tempfile.TemporaryDirectory() as folder:
        audio_path = download_audio(video_url, folder)
        transcript = transcribe_audio(audio_path)
    return parse_quiz(ask_gemini(build_prompt(transcript)))
