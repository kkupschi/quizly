# Quizly Backend

Backend for Quizly, an application that turns a YouTube video into a quiz with
ten questions and four answer options each.

The video is downloaded, converted into an audio file, transcribed with Whisper
AI and the transcript is then turned into a quiz by Google Gemini Flash.

Backend and frontend are separated and talk to each other through a REST API
only. Authentication runs over JWT stored in cookies that JavaScript cannot
read.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Connecting the Frontend](#connecting-the-frontend)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Tests](#tests)
- [Project Structure](#project-structure)
- [Admin Panel](#admin-panel)

## Tech Stack

- Python 3.12
- Django 6.1 and Django REST Framework
- SimpleJWT with token blacklist
- yt-dlp for the download
- FFmpeg and Whisper AI for the transcription
- Google Gemini Flash for the quiz generation
- SQLite as database

## Requirements

### Python

Python 3.12 is recommended. Newer versions can cause trouble with the
dependencies of Whisper.

### FFmpeg

**FFmpeg has to be installed globally and available in the PATH.** Whisper AI
cannot process any audio file without FFmpeg.

**Windows through the terminal**

```bash
winget install --id Gyan.FFmpeg -e --source winget
```

**Windows by hand**

1. Download a current build from https://ffmpeg.org/download.html (Windows
   builds, usually from gyan.dev or BtbN)
2. Unpack the ZIP file, for example to `C:\ffmpeg`
3. The folder `bin` contains `ffmpeg.exe`
4. Right click on "This PC", then "Properties", then "Advanced system
   settings"
5. Under "Environment variables" add `C:\ffmpeg\bin` to the variable `Path`

**macOS**

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg
```

The terminal has to be restarted afterwards so that the PATH is picked up.
This can be checked with:

```bash
ffmpeg -version
```

### Gemini API Key

The key is free and can be created at https://ai.google.dev/.

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/kkupschi/quizly.git
cd quizly
```

**2. Create and activate a virtual environment**

Windows:

```bash
py -3.12 -m venv env
.\env\Scripts\Activate.ps1
```

macOS and Linux:

```bash
python3.12 -m venv env
source env/bin/activate
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Create the environment file**

```bash
cp .env.example .env
```

Then fill in the values as described under
[Environment Variables](#environment-variables).

**5. Prepare the database**

```bash
python manage.py migrate
```

**6. Create an account for the admin panel**

```bash
python manage.py createsuperuser
```

**7. Start the server**

```bash
python manage.py runserver
```

The backend then runs at http://127.0.0.1:8000/ and the admin panel at
http://127.0.0.1:8000/admin/.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | yes | Signing key of the Django project |
| `DEBUG` | no | `True` during development, `False` otherwise |
| `GEMINI_API_KEY` | yes | Key from https://ai.google.dev/ |
| `GEMINI_MODEL` | no | Gemini model used for the generation |

A new Django secret key can be generated with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`GEMINI_MODEL` defaults to `gemini-2.5-flash`. If that model answers with an
error, the backend automatically tries the models listed in
`GEMINI_FALLBACK_MODELS` in `core/settings.py`. See
[Troubleshooting](#troubleshooting) for the models that can be used here.

## Connecting the Frontend

The frontend expects the backend at `http://127.0.0.1:8000/api/`. It is
usually started with the VS Code extension Live Server and then runs on port
5500.

The allowed addresses are listed in `core/settings.py` under
`CORS_ALLOWED_ORIGINS`. If the frontend runs on a different port, that port has
to be added there, otherwise the cookies never arrive.

## API Endpoints

All endpoints live under `/api/`. Authentication runs over the cookies
`access_token` and `refresh_token` that are set during the login.

### Authentication

| Method | Endpoint | Description | Login required |
|---|---|---|---|
| POST | `/api/register/` | Register a new user | no |
| POST | `/api/login/` | Log in, sets both cookies | no |
| POST | `/api/logout/` | Log out, blacklists the refresh token | yes |
| POST | `/api/token/refresh/` | Renew the access token | cookie required |

### Quiz

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/quizzes/` | Create a quiz from a YouTube address |
| GET | `/api/quizzes/` | Read all own quizzes |
| GET | `/api/quizzes/{id}/` | Read a single quiz |
| PATCH | `/api/quizzes/{id}/` | Change title and description |
| DELETE | `/api/quizzes/{id}/` | Delete a quiz and all of its questions |

Every quiz endpoint requires a login. Access to a quiz of another user leads to
403, an unknown id leads to 404.

The full description with request and response bodies is documented in
[docs/endpoints.md](docs/endpoints.md).

### Supported Video Addresses

When a quiz is created, every common YouTube format is accepted, among others
`watch?v=`, `youtu.be`, `shorts`, `live`, `embed` and `v`, each of them with
and without `www.` as well as with `m.` and `music.`. Appended parameters such
as `&t=42s` or `?si=` do no harm.

Every address is converted into the form
`https://www.youtube.com/watch?v=VIDEO_ID` and stored that way, so that the
frontend can embed the video reliably.

## Troubleshooting

### The generation takes several minutes

The first request downloads the Whisper model and the transcription runs on the
CPU. Depending on the machine and the length of the video this can take a few
minutes. A short video of one or two minutes is the fastest way to try the
feature out.

### The AI answers with 503 or the quiz is never created

A Gemini model can be overloaded or temporarily unavailable. The backend then
answers with status 400 and a readable message instead of a server error.

Two things help here:

1. Try again a little later.
2. Set another model in the `.env` file, for example:

```
GEMINI_MODEL=gemini-2.0-flash
```

Models that work well for this project:

| Model | Note |
|---|---|
| `gemini-2.5-flash` | Default, best quality of the generated questions |
| `gemini-2.0-flash` | Faster and less often overloaded |
| `gemini-2.5-flash-lite` | Fastest, slightly simpler questions |
| `gemini-flash-latest` | Always points to the newest Flash model |

If the configured model fails, the backend tries the fallback models on its own
before it gives up.

### The transcription fails

This almost always means that FFmpeg is missing or not in the PATH. See
[Requirements](#requirements).

## Tests

```bash
python manage.py test
```

The test suite covers both apps and checks the error cases next to the happy
paths: missing and invalid tokens, duplicate usernames and email addresses, a
password confirmation that does not match, quizzes of other users, unknown
quizzes, invalid video addresses and the fallback between the Gemini models.

## Project Structure

```
quizly/
├── core/           Project configuration, settings and root URLs
├── auth_app/       Registration, login, logout, token
│   ├── api/
│   │   ├── serializers.py  Checks the registration data
│   │   ├── urls.py         Routes of the auth endpoints
│   │   └── views.py        The four endpoints
│   ├── authentication.py   Reads the token from the cookie
│   └── utils.py            Cookies, blacklist, token creation
├── quiz_app/       Quizzes and questions
│   ├── api/
│   │   ├── serializers.py  Representation and validation of the input
│   │   ├── urls.py         Routes of the quiz endpoints
│   │   └── views.py        List, detail, update, delete
│   ├── functions.py        Download, transcription, Gemini request
│   ├── models.py           Quiz and Question
│   ├── permissions.py      Access to own quizzes only
│   └── utils.py            Address validation and quiz creation
├── docs/           Documentation of the endpoints
└── requirements.txt
```

## Admin Panel

Quizzes and their questions can be managed at http://127.0.0.1:8000/admin/.
The questions are embedded directly in the quiz and can also be reached on
their own.
