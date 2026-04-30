# TrainingBuddy Architecture

_Last updated: 2026-04-30_

## 1. Architecture overview

TrainingBuddy is a FastAPI application that integrates Strava, Twilio WhatsApp, OpenAI, and Supabase PostgreSQL.

The app follows a small modular architecture:

```text
app/
├── main.py
├── config.py
├── database.py
├── models.py
├── routes/
├── services/
└── utils/
```

Responsibilities stay separated:

- Routes expose HTTP endpoints.
- Services contain Strava, WhatsApp, coaching, and AI logic.
- Utils contain formatting, logging, and persistence helpers.
- `database.py` owns SQLAlchemy engine/session setup.
- `models.py` owns database table definitions.
- `config.py` centralizes environment variables and local fallback file paths.

## 2. Runtime flow

### 2.1 New Strava activity flow

```text
1. User finishes a Strava ride.
2. Strava sends a webhook POST to /webhook/strava.
3. Webhook route checks duplicate state in processed_events.
4. App fetches the full activity using object_id.
5. Strava service loads the current token for the default app user.
6. Strava service simplifies the activity into a usable dict.
7. Coaching service classifies the ride.
8. Coaching service builds weekly context.
9. AI service generates the ride interpretation.
10. Coaching service builds the final WhatsApp message.
11. WhatsApp service sends the message through Twilio.
12. Event is marked as processed.
```

### 2.2 Strava OAuth flow

```text
1. User opens /connect-strava.
2. Strava redirects to /strava/callback with an authorization code.
3. App exchanges the code for Strava tokens.
4. Tokens are saved to the strava_tokens table for the default app user.
5. If DATABASE_URL is absent, local development falls back to strava_tokens.json.
```

### 2.3 Manual recovery flow

```text
1. User runs scripts/recover_missed_activities.py.
2. Script fetches recent Strava activities.
3. Script checks processed event state.
4. Missed rides are sent to WhatsApp.
5. Activity IDs are saved as processed.
```

### 2.4 Manual resend flow

```text
1. User provides a Strava activity ID.
2. Script or one-liner fetches exact activity.
3. App builds message.
4. App sends WhatsApp message.
5. This path does not need to modify processed event state.
```

## 3. Database model

Current SQLAlchemy models:

```text
app_users
- id
- name
- whatsapp_number
- strava_athlete_id
- created_at
- updated_at

strava_tokens
- id
- user_id
- athlete_id
- access_token
- refresh_token
- expires_at
- created_at
- updated_at

processed_events
- id
- user_id
- strava_object_id
- object_type
- aspect_type
- processed_at
- status
- error_message
```

`processed_events` keeps the current global uniqueness behavior on `strava_object_id`, `object_type`, and `aspect_type`. A nullable `user_id` is populated when Strava `owner_id` maps to the current app user, preparing the app for future user-scoped routing.

## 4. Persistence behavior

When `DATABASE_URL` is configured:

- Strava tokens are stored in PostgreSQL.
- Processed webhook events are stored in PostgreSQL.
- Tables are initialized at startup through SQLAlchemy metadata creation.

When `DATABASE_URL` is not configured:

- Local development falls back to `strava_tokens.json`.
- Local development falls back to `processed_events.json`.
- These runtime files remain ignored by Git.

## 5. Main modules

### `app/main.py`

Creates the FastAPI app, initializes database tables on startup when configured, and registers routers.

### `app/config.py`

Centralizes environment variables and local fallback paths, including `DATABASE_URL`.

### `app/database.py`

Creates the SQLAlchemy engine/session and initializes database tables. If `DATABASE_URL` is absent, startup uses local JSON fallback mode.

### `app/models.py`

Defines `AppUser`, `StravaToken`, and `ProcessedEvent`.

### `app/routes/strava.py`

Contains manual Strava endpoints:

```text
GET /connect-strava
GET /strava/callback
GET /strava/activities
GET /send-latest-activity-whatsapp
GET /test-whatsapp
```

### `app/routes/webhook.py`

Contains Strava webhook endpoints:

```text
GET /webhook/strava
POST /webhook/strava
GET /debug/weekly-context
```

It must continue to preserve Strava webhook verification and duplicate protection.

### `app/services/strava_service.py`

Handles Strava OAuth, token refresh, activity fetches, activity simplification, and weekly context.

### `app/services/coaching_service.py`

Contains deterministic coaching logic and final message assembly.

### `app/services/ai_service.py`

Generates only the short PT-BR training interpretation and keeps deterministic fallback behavior.

### `app/services/whatsapp_service.py`

Sends WhatsApp messages through Twilio.

### `app/utils/storage.py`

Owns token and processed-event persistence. It uses PostgreSQL when `DATABASE_URL` is configured and JSON fallback files only when it is not.

## 6. Deployment architecture

Railway runs the app through the Procfile:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required production persistence variable:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

No secrets should be committed to GitHub.

## 7. Remaining multi-user work

The database model is multi-user-ready, but the product still behaves as a one-user MVP. Remaining work includes explicit onboarding, per-user WhatsApp routing, and changing duplicate uniqueness to user-scoped behavior after webhook owner routing is explicit.
