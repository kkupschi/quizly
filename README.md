# Quizly Backend

Backend für Quizly, eine Anwendung, die aus einem YouTube Video automatisch ein
Quiz mit zehn Fragen und je vier Antwortmöglichkeiten erzeugt.

Das Video wird heruntergeladen, in eine Audiodatei umgewandelt, mit Whisper AI
transkribiert und das Transkript anschließend von Google Gemini Flash zu einem
Quiz verarbeitet.

Backend und Frontend sind getrennt und kommunizieren ausschließlich über eine
REST API. Die Authentifizierung läuft über JWT in HTTP-Only-Cookies.

## Technologien

- Python 3.12
- Django 6.1 und Django REST Framework
- SimpleJWT mit Token-Blacklist
- yt-dlp für den Download
- FFmpeg und Whisper AI für die Transkription
- Google Gemini Flash für die Quizerstellung
- SQLite als Datenbank

## Voraussetzungen

### Python

Python 3.12 wird empfohlen. Neuere Versionen können Probleme mit den
Abhängigkeiten von Whisper verursachen.

### FFmpeg

**FFmpeg muss global installiert und im PATH verfügbar sein.** Whisper AI kann
ohne FFmpeg keine Audiodateien verarbeiten.

**Windows über das Terminal**

```bash
winget install --id Gyan.FFmpeg -e --source winget
```

**Windows manuell**

1. Aktuelles Build von https://ffmpeg.org/download.html laden (Windows builds,
   meist von gyan.dev oder BtbN)
2. ZIP entpacken, zum Beispiel nach `C:\ffmpeg`
3. Im Ordner `bin` liegt die `ffmpeg.exe`
4. Rechtsklick auf "Dieser PC", dann "Eigenschaften", dann "Erweiterte
   Systemeinstellungen"
5. Unter "Umgebungsvariablen" den Eintrag `C:\ffmpeg\bin` zur Variable `Path`
   hinzufügen

**macOS**

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg
```

Nach der Installation muss das Terminal neu gestartet werden, damit der PATH
übernommen wird. Prüfen lässt sich das mit:

```bash
ffmpeg -version
```

### Gemini API Key

Der Key ist kostenlos und wird über https://ai.google.dev/ erstellt.

## Installation

**1. Repository klonen**

```bash
git clone https://github.com/kkupschi/quizly.git
cd quizly
```

**2. Virtuelle Umgebung anlegen und aktivieren**

Windows:

```bash
py -3.12 -m venv env
.\env\Scripts\Activate.ps1
```

macOS und Linux:

```bash
python3.12 -m venv env
source env/bin/activate
```

**3. Abhängigkeiten installieren**

```bash
pip install -r requirements.txt
```

**4. Umgebungsvariablen setzen**

Die Datei `.env.example` als Vorlage nach `.env` kopieren und ausfüllen:

```
SECRET_KEY=dein-django-secret-key
DEBUG=True
GEMINI_API_KEY=dein-google-gemini-api-key
```

Einen neuen Django Secret Key erzeugt man mit:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Die `.env` ist bewusst nicht Teil des Repositories und darf nicht committet
werden.

**5. Datenbank vorbereiten**

```bash
python manage.py migrate
```

**6. Zugang für das Adminpanel anlegen**

```bash
python manage.py createsuperuser
```

**7. Server starten**

```bash
python manage.py runserver
```

Das Backend läuft anschließend unter http://127.0.0.1:8000/ und das Adminpanel
unter http://127.0.0.1:8000/admin/.

## Frontend anbinden

Das Frontend erwartet das Backend unter `http://127.0.0.1:8000/api/`. Es wird
üblicherweise mit der VS Code Erweiterung Live Server gestartet und läuft dann
auf Port 5500.

Die erlaubten Adressen stehen in `core/settings.py` unter
`CORS_ALLOWED_ORIGINS`. Läuft das Frontend auf einem anderen Port, muss dieser
dort ergänzt werden, sonst kommen die Cookies nicht an.

## API Endpunkte

Alle Endpunkte liegen unter `/api/`. Die Authentifizierung erfolgt über die
Cookies `access_token` und `refresh_token`, die beim Login gesetzt werden.

### Authentifizierung

| Methode | Endpunkt | Beschreibung | Anmeldung nötig |
|---|---|---|---|
| POST | `/api/register/` | Neuen Benutzer registrieren | nein |
| POST | `/api/login/` | Anmelden, setzt beide Cookies | nein |
| POST | `/api/logout/` | Abmelden, sperrt den Refreshtoken | ja |
| POST | `/api/token/refresh/` | Zugriffstoken erneuern | Cookie nötig |

### Quiz

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| POST | `/api/quizzes/` | Quiz aus einer YouTube Adresse erzeugen |
| GET | `/api/quizzes/` | Alle eigenen Quizze abrufen |
| GET | `/api/quizzes/{id}/` | Ein einzelnes Quiz abrufen |
| PATCH | `/api/quizzes/{id}/` | Titel und Beschreibung ändern |
| DELETE | `/api/quizzes/{id}/` | Quiz und alle Fragen löschen |

Alle Quiz Endpunkte setzen eine Anmeldung voraus. Ein Zugriff auf ein fremdes
Quiz führt zu 403, eine unbekannte Kennung zu 404.

Die vollständige Beschreibung mit Request und Response Bodies steht in
[docs/endpoints.md](docs/endpoints.md).

### Unterstützte Videoadressen

Beim Anlegen eines Quiz werden alle gängigen YouTube Formate akzeptiert, unter
anderem `watch?v=`, `youtu.be`, `shorts`, `live`, `embed` und `v`, jeweils mit
und ohne `www.` sowie mit `m.` und `music.`. Angehängte Parameter wie `&t=42s`
oder `?si=` stören nicht.

Jede Adresse wird intern in die Form
`https://www.youtube.com/watch?v=VIDEO_ID` gebracht und so gespeichert, damit
das Frontend das Video zuverlässig einbetten kann.

## Tests

```bash
python manage.py test
```

Die Testsuite deckt beide Apps ab und prüft neben den Erfolgsfällen vor allem
die Fehlerfälle: fehlende und ungültige Token, doppelte Benutzernamen und
Mailadressen, abweichende Passwortbestätigung, fremde und unbekannte Quizze
sowie ungültige Videoadressen.

## Projektstruktur

```
quizly/
├── core/           Projektkonfiguration, Einstellungen und Haupt URLs
├── auth_app/       Registrierung, Anmeldung, Abmeldung, Token
│   ├── authentication.py   Liest den Token aus dem Cookie
│   ├── serializers.py      Prüft die Registrierungsdaten
│   ├── utils.py            Cookies, Blacklist, Tokenerzeugung
│   └── views.py            Die vier Endpunkte
├── quiz_app/       Quizze und Fragen
│   ├── models.py           Quiz und Question
│   ├── permissions.py      Zugriff nur auf eigene Quizze
│   ├── serializers.py      Darstellung und Prüfung der Eingaben
│   ├── utils.py            Adressprüfung und Quizerzeugung
│   └── views.py            Liste, Detail, Änderung, Löschung
├── docs/           Dokumentation der Endpunkte
└── requirements.txt
```

## Adminpanel

Unter http://127.0.0.1:8000/admin/ lassen sich Quizze und ihre Fragen pflegen.
Die Fragen sind direkt im Quiz eingebettet und zusätzlich einzeln erreichbar.
