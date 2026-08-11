# Quizly - Endpoint-Dokumentation

> Referenz für die Backend-Implementierung. Quelle: Vorgabe Developer Akademie.

## Authentication

### POST /api/register/

Registriert einen neuen Benutzer.

**Request Body**

```json
{
  "username": "your_username",
  "password": "your_password",
  "confirmed_password": "your_confirmed_password",
  "email": "your_email@example.com"
}
```

**Success Response** - Benutzer wurde erfolgreich erstellt.

```json
{
  "detail": "User created successfully!"
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 201 | Benutzer erfolgreich erstellt. |
| 400 | Ungültige Daten. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: keine

---

### POST /api/login/

Meldet den Benutzer an und setzt Auth-Cookies.

**Request Body**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Success Response** - Login war erfolgreich. Cookies werden gesetzt.

```json
{
  "detail": "Login successfully!",
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "your_email@example.com"
  }
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Erfolgreicher Login. |
| 401 | Ungültige Anmeldedaten. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: keine
- Extra: Setzt `access_token` und `refresh_token` als Cookies.

---

### POST /api/logout/

Meldet den Benutzer ab und löscht alle Token.

**Request Body**

```json
{}
```

**Success Response** - Der Benutzer wird ausgeloggt, alle Tokens sind ungültig.

```json
{
  "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Erfolgreicher Logout. |
| 401 | Nicht authentifiziert. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich.
- Extra: Cookies `access_token` und `refresh_token` werden entfernt.

---

### POST /api/token/refresh/

Erneuert den Access-Token mithilfe des Refresh-Tokens.

**Request Body**

```json
{}
```

**Success Response** - Gibt einen neuen Access-Token zurück.

```json
{
  "detail": "Token refreshed"
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Token erfolgreich erneuert. |
| 401 | Refresh Token ungültig oder fehlt. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung über `refresh_token`-Cookie erforderlich.
- Extra: Setzt neuen `access_token` Cookie.

---

## Quiz Management

### POST /api/quizzes/

Erstellt ein neues Quiz basierend auf einer YouTube-URL.

**Request Body**

```json
{
  "url": "https://www.youtube.com/watch?v=example"
}
```

**Success Response** - Gibt das erstellte Quiz mit allen Fragen zurück.

```json
{
  "id": 1,
  "title": "Quiz Title",
  "description": "Quiz Description",
  "created_at": "2023-07-29T12:34:56.789Z",
  "updated_at": "2023-07-29T12:34:56.789Z",
  "video_url": "https://www.youtube.com/watch?v=example",
  "questions": [
    {
      "id": 1,
      "question_title": "Question 1",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A",
      "created_at": "2023-07-29T12:34:56.789Z",
      "updated_at": "2023-07-29T12:34:56.789Z"
    }
  ]
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 201 | Quiz erfolgreich erstellt. |
| 400 | Ungültige URL oder Anfragedaten. |
| 401 | Nicht authentifiziert. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich.

---

### GET /api/quizzes/

Ruft alle Quizzes des authentifizierten Benutzers ab.

**Success Response** - Liste aller Quizzes des Benutzers mit Fragen.

```json
[
  {
    "id": 1,
    "title": "Quiz Title",
    "description": "Quiz Description",
    "created_at": "2023-07-29T12:34:56.789Z",
    "updated_at": "2023-07-29T12:34:56.789Z",
    "video_url": "https://www.youtube.com/watch?v=example",
    "questions": [
      {
        "id": 1,
        "question_title": "Question 1",
        "question_options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "Option A"
      }
    ]
  }
]
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Quizzes erfolgreich abgerufen. |
| 401 | Nicht authentifiziert. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich.

---

### GET /api/quizzes/{id}/

Ruft ein spezifisches Quiz des Benutzers ab.

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | - | Die ID des Quiz, das abgerufen werden soll. |

**Success Response** - Das spezifische Quiz mit allen Fragen und Details.

```json
{
  "id": 1,
  "title": "Quiz Title",
  "description": "Quiz Description",
  "created_at": "2023-07-29T12:34:56.789Z",
  "updated_at": "2023-07-29T12:34:56.789Z",
  "video_url": "https://www.youtube.com/watch?v=example",
  "questions": [
    {
      "id": 1,
      "question_title": "Question 1",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A"
    }
  ]
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Quiz erfolgreich abgerufen. |
| 401 | Nicht authentifiziert. |
| 403 | Zugriff verweigert - Quiz gehört nicht dem Benutzer. |
| 404 | Quiz nicht gefunden. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich. Benutzer kann nur eigene Quizzes abrufen.

---

### PATCH /api/quizzes/{id}/

Aktualisiert einzelne Felder eines Quiz (partielle Aktualisierung).

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | - | Die ID des Quiz, das aktualisiert werden soll. |

**Request Body**

```json
{
  "title": "Partially Updated Title",
  "description": "Partially Updated Description"
}
```

**Success Response** - Das aktualisierte Quiz mit allen Details.

```json
{
  "id": 1,
  "title": "Partially Updated Title",
  "description": "Quiz Description",
  "created_at": "2023-07-29T12:34:56.789Z",
  "updated_at": "2023-07-29T14:45:12.345Z",
  "video_url": "https://www.youtube.com/watch?v=example",
  "questions": [
    {
      "id": 1,
      "question_title": "Question 1",
      "question_options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option A"
    }
  ]
}
```

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 200 | Quiz erfolgreich aktualisiert. |
| 400 | Ungültige Anfragedaten. |
| 401 | Nicht authentifiziert. |
| 403 | Zugriff verweigert - Quiz gehört nicht dem Benutzer. |
| 404 | Quiz nicht gefunden. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich. Benutzer kann nur eigene Quizzes bearbeiten.

---

### DELETE /api/quizzes/{id}/

Löscht ein Quiz und alle zugehörigen Fragen permanent.

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | - | Die ID des Quiz, das gelöscht werden soll. |

**Success Response** - Keine Antwortdaten bei erfolgreichem Löschen (`null`).

**Status Codes**

| Code | Bedeutung |
| --- | --- |
| 204 | Quiz erfolgreich gelöscht. |
| 401 | Nicht authentifiziert. |
| 403 | Zugriff verweigert - Quiz gehört nicht dem Benutzer. |
| 404 | Quiz nicht gefunden. |
| 500 | Interner Serverfehler. |

- Rate Limits: keine
- Permissions: Authentifizierung erforderlich. Benutzer kann nur eigene Quizzes löschen.
- Extra: Warnung - das Löschen ist permanent und kann nicht rückgängig gemacht werden.
