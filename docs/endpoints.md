# Quizly API Endpoints

> Reference for the backend implementation. Source: specification of the Developer Akademie.

## Authentication

### POST /api/register/

Registers a new user.

**Request Body**

```json
{
  "username": "your_username",
  "password": "your_password",
  "confirmed_password": "your_confirmed_password",
  "email": "your_email@example.com"
}
```

**Success Response**: the user was created.

```json
{
  "detail": "User created successfully!"
}
```

**Status Codes**

| Code | Meaning |
| --- | --- |
| 201 | User created successfully. |
| 400 | Invalid data. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: none

---

### POST /api/login/

Logs the user in and sets the auth cookies.

**Request Body**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Success Response**: the login succeeded and both cookies are set.

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

| Code | Meaning |
| --- | --- |
| 200 | Login successful. |
| 401 | Invalid credentials. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: none
- Extra: sets `access_token` and `refresh_token` as cookies.

---

### POST /api/logout/

Logs the user out and deletes all tokens.

**Request Body**

```json
{}
```

**Success Response**: the user is logged out and every token is invalid.

```json
{
  "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
}
```

**Status Codes**

| Code | Meaning |
| --- | --- |
| 200 | Logout successful. |
| 401 | Not authenticated. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required.
- Extra: the cookies `access_token` and `refresh_token` are removed.

---

### POST /api/token/refresh/

Renews the access token with the help of the refresh token.

**Request Body**

```json
{}
```

**Success Response**: returns a new access token.

```json
{
  "detail": "Token refreshed"
}
```

**Status Codes**

| Code | Meaning |
| --- | --- |
| 200 | Token renewed successfully. |
| 401 | Refresh token invalid or missing. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication through the `refresh_token` cookie required.
- Extra: sets a new `access_token` cookie.

---

## Quiz Management

### POST /api/quizzes/

Creates a new quiz based on a YouTube URL.

**Request Body**

```json
{
  "url": "https://www.youtube.com/watch?v=example"
}
```

**Success Response**: returns the created quiz with all questions.

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

| Code | Meaning |
| --- | --- |
| 201 | Quiz created successfully. |
| 400 | Invalid URL or request data. |
| 401 | Not authenticated. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required.

---

### GET /api/quizzes/

Reads all quizzes of the authenticated user.

**Success Response**: list of all quizzes of the user with their questions.

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

| Code | Meaning |
| --- | --- |
| 200 | Quizzes read successfully. |
| 401 | Not authenticated. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required.

---

### GET /api/quizzes/{id}/

Reads one specific quiz of the user.

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | int | The id of the quiz that should be read. |

**Success Response**: the requested quiz with all questions and details.

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

| Code | Meaning |
| --- | --- |
| 200 | Quiz read successfully. |
| 401 | Not authenticated. |
| 403 | Access denied, the quiz belongs to another user. |
| 404 | Quiz not found. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required. A user can read own quizzes only.

---

### PATCH /api/quizzes/{id}/

Updates single fields of a quiz (partial update).

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | int | The id of the quiz that should be updated. |

**Request Body**

```json
{
  "title": "Partially Updated Title",
  "description": "Partially Updated Description"
}
```

**Success Response**: the updated quiz with all details.

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

| Code | Meaning |
| --- | --- |
| 200 | Quiz updated successfully. |
| 400 | Invalid request data. |
| 401 | Not authenticated. |
| 403 | Access denied, the quiz belongs to another user. |
| 404 | Quiz not found. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required. A user can edit own quizzes only.

---

### DELETE /api/quizzes/{id}/

Deletes a quiz and all of its questions permanently.

**URL Parameters**

| Name | Type | Description |
| --- | --- | --- |
| id | int | The id of the quiz that should be deleted. |

**Success Response**: no response data after a successful delete (`null`).

**Status Codes**

| Code | Meaning |
| --- | --- |
| 204 | Quiz deleted successfully. |
| 401 | Not authenticated. |
| 403 | Access denied, the quiz belongs to another user. |
| 404 | Quiz not found. |
| 500 | Internal server error. |

- Rate limits: none
- Permissions: authentication required. A user can delete own quizzes only.
- Extra: warning, the delete is permanent and cannot be undone.
