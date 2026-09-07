import json
import os
import tempfile

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors

WHISPER_MODEL = 'base'
QUESTION_COUNT = 10
OPTION_COUNT = 4
AUDIO_NAME = 'audio'
RESPONSE_CONFIG = {'response_mime_type': 'application/json'}

AI_UNAVAILABLE = (
    'The AI could not be reached. Please try again later or switch '
    'GEMINI_MODEL in your .env file to another model.'
)

PROMPT = """You are a tool that turns a transcript into a quiz.

Create exactly {count} questions about the following content. Every question
has exactly {options} answer options and exactly one of them is correct. The
correct answer has to appear word by word in the answer options.

Answer with JSON in this structure and with nothing else:
{{
  "title": "short title of the quiz",
  "description": "one or two sentences about the content",
  "questions": [
    {{
      "question_title": "the question",
      "question_options": ["A", "B", "C", "D"],
      "answer": "A"
    }}
  ]
}}

Use the same language as the transcript.

Transcript:
{transcript}
"""


class QuizGenerationError(Exception):
    """Error that can occur while a quiz is generated."""


def download_audio(video_url, target_dir):
    """Downloads the audio track of a video and returns its file path."""
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
    """Runs the download and reports failures in a readable way."""
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([video_url])
    except yt_dlp.utils.DownloadError as error:
        raise QuizGenerationError(
            'The video could not be downloaded.'
        ) from error
    return os.path.join(target_dir, f'{AUDIO_NAME}.mp3')


def run_whisper(audio_path):
    """Runs Whisper on the audio file and returns the plain transcript."""
    try:
        model = whisper.load_model(WHISPER_MODEL)
        return model.transcribe(audio_path)['text'].strip()
    except (OSError, RuntimeError) as error:
        raise QuizGenerationError(
            'The audio could not be transcribed. Please make sure that '
            'FFmpeg is installed and available in your PATH.'
        ) from error


def transcribe_audio(audio_path):
    """Turns an audio file into text and rejects silent videos."""
    transcript = run_whisper(audio_path)
    if not transcript:
        raise QuizGenerationError('The video contains no spoken language.')
    return transcript


def build_prompt(transcript):
    """Builds the instruction for the AI out of the transcript."""
    return PROMPT.format(
        count=QUESTION_COUNT,
        options=OPTION_COUNT,
        transcript=transcript,
    )


def gemini_models():
    """Returns the configured model followed by the fallback models."""
    models = [settings.GEMINI_MODEL]
    for name in settings.GEMINI_FALLBACK_MODELS:
        if name not in models:
            models.append(name)
    return models


def request_quiz(client, model, prompt):
    """Sends the instruction to one model and returns the answer text."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=RESPONSE_CONFIG,
    )
    return response.text


def ask_gemini(prompt):
    """Asks Gemini for the quiz and tries the next model on failure."""
    if not settings.GEMINI_API_KEY:
        raise QuizGenerationError('No access to the AI is configured.')
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    last_error = None
    for model in gemini_models():
        try:
            return request_quiz(client, model, prompt)
        except genai_errors.APIError as error:
            last_error = error
    raise QuizGenerationError(AI_UNAVAILABLE) from last_error


def strip_code_fence(text):
    """Removes a possible fence of backticks around the JSON."""
    cleaned = (text or '').strip()
    if not cleaned.startswith('```'):
        return cleaned
    cleaned = cleaned.split('\n', 1)[-1]
    return cleaned.rsplit('```', 1)[0].strip()


def validate_question(question):
    """Checks a single question for completeness."""
    options = question.get('question_options')
    if not question.get('question_title'):
        raise QuizGenerationError('A question of the AI has no text.')
    if not isinstance(options, list) or len(options) != OPTION_COUNT:
        raise QuizGenerationError(
            f'A question does not have {OPTION_COUNT} answer options.'
        )
    if question.get('answer') not in options:
        raise QuizGenerationError(
            'The correct answer is missing in the answer options.'
        )


def validate_quiz(data):
    """Checks whether the answer of the AI has the expected structure."""
    questions = data.get('questions') if isinstance(data, dict) else None
    if not isinstance(questions, list):
        raise QuizGenerationError('The answer of the AI contains no quiz.')
    if len(questions) != QUESTION_COUNT:
        raise QuizGenerationError(
            f'The AI did not deliver {QUESTION_COUNT} questions.'
        )
    for question in questions:
        validate_question(question)


def parse_quiz(raw_text):
    """Reads the quiz out of the answer of the AI and validates it."""
    try:
        data = json.loads(strip_code_fence(raw_text))
    except json.JSONDecodeError as error:
        raise QuizGenerationError(
            'The answer of the AI was no valid JSON.'
        ) from error
    validate_quiz(data)
    return data


def generate_quiz_data(video_url):
    """Creates title, description and questions for a video."""
    with tempfile.TemporaryDirectory() as folder:
        audio_path = download_audio(video_url, folder)
        transcript = transcribe_audio(audio_path)
    return parse_quiz(ask_gemini(build_prompt(transcript)))
