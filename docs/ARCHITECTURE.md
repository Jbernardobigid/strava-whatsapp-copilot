# TrainingBuddy Architecture

_Last updated: 2026-04-24_

## 1. Architecture overview

TrainingBuddy is a FastAPI application that integrates Strava, Twilio WhatsApp, and OpenAI.

The app follows a small modular architecture:

```text
app/
├── main.py
├── config.py
├── routes/
├── services/
└── utils/
```

The system is designed around clear separation of responsibilities:

- Routes expose HTTP endpoints.
- Services contain product/business logic.
- Utils contain reusable infrastructure helpers.
- Config centralizes environment variables.

## 2. Runtime flow

### 2.1 New Strava activity flow

```text
1. User finishes a Strava ride.
2. Strava sends a webhook POST to /webhook/strava.
3. Webhook route checks deduplication.
4. App fetches full activity using object_id.
5. Strava service simplifies the activity into a usable dict.
6. Coaching service classifies the ride.
7. Coaching service builds weekly context.
8. AI service generates the ride interpretation.
9. Coaching service builds the final WhatsApp message.
10. WhatsApp service sends the message through Twilio.
11. Event is marked as processed.
```

### 2.2 Manual recovery flow

```text
1. User runs scripts/recover_missed_activities.py.
2. Script fetches recent Strava activities.
3. Script checks processed event keys.
4. Missed rides are sent to WhatsApp.
5. Activity IDs are saved as processed.
```

### 2.3 Manual resend flow

```text
1. User provides a Strava activity ID.
2. Script or one-liner fetches exact activity.
3. App builds message.
4. App sends WhatsApp message.
5. This path does not need to modify processed_events.json.
```

## 3. Folder structure

```text
app/
├── __init__.py
├── main.py
├── config.py
├── routes/
│   ├── __init__.py
│   ├── health.py
│   ├── strava.py
│   └── webhook.py
├── services/
│   ├── __init__.py
│   ├── ai_service.py
│   ├── coaching_service.py
│   ├── strava_service.py
│   └── whatsapp_service.py
└── utils/
    ├── __init__.py
    ├── formatters.py
    ├── logger.py
    └── storage.py
```

## 4. Main modules

## 4.1 `app/main.py`

Creates the FastAPI app and registers routers.

Expected responsibilities:

- Create `FastAPI(title="Strava WhatsApp Copilot")`
- Include health routes
- Include Strava routes
- Include webhook routes
- Initialize logging

This file should remain small.

## 4.2 `app/config.py`

Centralizes environment variables and file paths.

Typical values:

```python
TOKEN_FILE
PROCESSED_EVENTS_FILE
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER
YOUR_WHATSAPP_NUMBER
STRAVA_CLIENT_ID
STRAVA_CLIENT_SECRET
STRAVA_REDIRECT_URI
STRAVA_VERIFY_TOKEN
OPENAI_API_KEY
OPENAI_MODEL
```

No secrets should be committed to GitHub.

## 4.3 `app/routes/health.py`

Provides basic status endpoints:

```text
GET /
GET /health
```

Used to confirm local/Railway availability.

## 4.4 `app/routes/strava.py`

Contains user-facing/manual Strava endpoints:

```text
GET /connect-strava
GET /strava/callback
GET /strava/activities
GET /send-latest-activity-whatsapp
GET /test-whatsapp
```

## 4.5 `app/routes/webhook.py`

Contains Strava webhook endpoints:

```text
GET /webhook/strava
POST /webhook/strava
GET /debug/weekly-context
```

Responsibilities:

- Verify Strava webhook subscription challenge.
- Receive activity events.
- Ignore duplicates.
- Fetch exact activity by ID.
- Send WhatsApp message.
- Mark event as processed.

## 4.6 `app/services/strava_service.py`

Handles Strava API interactions.

Responsibilities:

- Refresh access tokens.
- Build Strava authorization URL.
- Exchange authorization code for token.
- Fetch latest activity.
- Fetch activity by ID.
- Fetch recent activities.
- Simplify raw Strava activity data.
- Build weekly context.

## 4.7 `app/services/coaching_service.py`

Contains core product intelligence.

Responsibilities:

- Translate Strava activity types to PT-BR.
- Classify rides.
- Build ride title.
- Generate fallback interpretation.
- Generate next-day suggestion.
- Call AI interpretation.
- Build final WhatsApp message.

## 4.8 `app/services/ai_service.py`

Handles OpenAI calls.

Responsibilities:

- Receive activity and weekly context.
- Generate short PT-BR ride interpretation.
- Apply fallback if OpenAI fails.
- Log success/failure.

The AI should not own business-critical workflow decisions.

## 4.9 `app/services/whatsapp_service.py`

Handles Twilio WhatsApp sending.

Responsibilities:

- Validate Twilio env vars.
- Send WhatsApp message.
- Log Twilio Message SID.

Important: Twilio returning a Message SID means accepted by Twilio, not necessarily delivered to WhatsApp.

## 4.10 `app/utils/storage.py`

Handles file-based persistence.

Responsibilities:

- Load/save Strava tokens.
- Load/save processed webhook event keys.
- Build deduplication event keys.

Current deduplication key:

```text
object_type:aspect_type:object_id
```

Example:

```text
activity:create:18236736799
```

## 4.11 `app/utils/formatters.py`

Formatting helpers:

- `format_datetime_pt_br`
- `format_number_pt_br`
- `format_duration_pt_br`
- `normalize_activity_name`

## 4.12 `app/utils/logger.py`

Central logging setup.

Current behavior:

- Console logging.
- File logging to `logs/app.log`.
- Rotating file handler.

## 5. Deployment architecture

The app is deployed on Railway using a Procfile:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Railway injects the `$PORT` value at runtime.

## 6. Persistence warning

The current architecture still has temporary file-based persistence.

This is acceptable for MVP but should be changed before serious production usage.

Recommended future architecture:

```text
Railway FastAPI app
        ↓
PostgreSQL / Supabase
        ↓
users, strava_tokens, processed_events, sent_messages
```
