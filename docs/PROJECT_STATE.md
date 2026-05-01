# TrainingBuddy / Strava WhatsApp Copilot — Project State

_Last updated: 2026-05-01_

## 1. Project overview

TrainingBuddy, also referred to as Strava WhatsApp Copilot, is a personal cycling assistant that listens for new Strava activities and sends a WhatsApp message in Brazilian Portuguese with a short training interpretation.

The app currently works as an event-driven workflow:

```text
Strava activity created
        ↓
Strava webhook with owner_id
        ↓
Railway-hosted FastAPI app
        ↓
Resolve owner_id to app_users.strava_athlete_id
        ↓
Check processed_events in Supabase PostgreSQL
        ↓
Load Strava token for the resolved app user
        ↓
Fetch full Strava activity by object_id
        ↓
Classify ride using metrics
        ↓
Generate AI-assisted training interpretation
        ↓
Send WhatsApp message through Twilio to the user's configured destination
        ↓
Record sent message metadata in PostgreSQL
        ↓
Record processed event in PostgreSQL with user_id when known
```

The product still behaves as a one-user MVP by default, but OAuth and webhook handling now use explicit Strava athlete-to-user mapping where available.

## 2. Current deployed status

The app has been deployed to Railway.

Production base URL:

```text
https://web-production-d4872.up.railway.app
```

Health check endpoint:

```text
https://web-production-d4872.up.railway.app/health
```

Expected response:

```json
{"status":"ok"}
```

Current Strava webhook callback URL:

```text
https://web-production-d4872.up.railway.app/webhook/strava
```

Current Strava webhook subscription ID observed during setup:

```text
342486
```

Twilio delivery status callback URL to configure in Twilio:

```text
https://web-production-d4872.up.railway.app/webhook/twilio/status
```

## 3. What is working

The following features are currently working:

- FastAPI app running locally and on Railway.
- Strava OAuth connection.
- `/connect-strava` redirects directly to Strava authorization.
- `/strava/callback` saves tokens and associates returned Strava `athlete_id` with an `app_users` row.
- `/debug/strava-token-status` returns safe token metadata without token values.
- Strava token refresh flow.
- Strava webhook verification endpoint.
- Strava webhook subscription pointing to Railway.
- Webhook `owner_id` routing to the matching `app_users.strava_athlete_id` when configured.
- Fetching exact activity by webhook `object_id` using the resolved user's Strava token.
- WhatsApp sending through Twilio using the resolved user's configured WhatsApp destination when available.
- Current one-user/default behavior remains available as fallback for manual/local flows.
- PT-BR message generation.
- Strava token persistence backed by PostgreSQL `app_users` and `strava_tokens` tables when `DATABASE_URL` is configured.
- Local `strava_tokens.json` fallback only when `DATABASE_URL` is not configured.
- Duplicate webhook protection backed by a PostgreSQL `processed_events` table through `DATABASE_URL`.
- Processed events store `user_id` when Strava `owner_id` maps to an app user.
- Twilio sent-message metadata persistence backed by PostgreSQL `sent_messages` when `DATABASE_URL` is configured.
- Sent messages store `user_id` and `strava_activity_id` when the webhook owner maps to an app user.
- `/webhook/twilio/status` updates sent-message delivery status by Twilio Message SID without returning phone numbers or token values.
- Recovery script for missed activities.
- Manual resend by activity ID.
- Logging to `logs/app.log` locally.
- AI-assisted ride interpretation using OpenAI.
- Improved ride classification using power, heart rate, suffer score, achievements, PR count, and laps.
- Basic unittest coverage for core formatters, activity-name normalization, webhook event keys, ride classification, duplicate event database handling, database token persistence, Strava redirect behavior, safe token status metadata, sent-message persistence, Twilio status callback updates, app-user lookup, and webhook owner routing.
- Repository hygiene cleaned up so runtime files stay untracked, private-key patterns are ignored, and the activity export helper is standardized as `scripts/export_activity_json.py`.

## 4. Current architecture summary

The project is structured as:

```text
app/
├── main.py
├── config.py
├── database.py
├── models.py
├── routes/
│   ├── health.py
│   ├── strava.py
│   ├── twilio.py
│   └── webhook.py
├── services/
│   ├── ai_service.py
│   ├── coaching_service.py
│   ├── strava_service.py
│   └── whatsapp_service.py
└── utils/
    ├── formatters.py
    ├── logger.py
    └── storage.py

scripts/
├── recover_missed_activities.py
├── resend_activity.py
└── export_activity_json.py
```

Database-backed persistence covers Strava tokens, duplicate webhook protection, Twilio sent-message status tracking, and basic app-user mapping when `DATABASE_URL` is configured. The app initializes tables safely at startup with SQLAlchemy metadata creation and falls back to local JSON files only for local token/event development without `DATABASE_URL`.

## 5. Current message behavior

WhatsApp message content is unchanged by the onboarding and owner-routing work. The AI layer still writes only the short training interpretation under:

```text
Leitura do treino:
```

Deterministic code still controls activity fetching, ride classification, weekly context, message structure, formatting, next-day suggestion, duplicate handling, and fallback behavior.

## 6. Current known limitations

### 6.1 Multi-user behavior is basic but not complete

The app now maps Strava `athlete_id` / webhook `owner_id` to `app_users`, but it is still not a full multi-user product.

Remaining work:

- explicit user onboarding UI or command flow
- explicit WhatsApp number verification per user
- per-user settings and preferences
- fully user-scoped duplicate uniqueness after routing is mature
- safer admin tooling for user mappings

### 6.2 Unknown webhook owners are skipped

If a Strava webhook arrives with an `owner_id` that does not map to an existing user, the app logs a safe warning and returns a successful webhook response without fetching the activity or sending WhatsApp. This avoids sending a user's activity through the wrong token or destination.

### 6.3 Persistence is database-backed with local fallback

The app uses PostgreSQL tables configured by `DATABASE_URL` for:

- `app_users`
- `strava_tokens`
- `processed_events`
- `sent_messages`

When `DATABASE_URL` is not configured, local development falls back to:

- `strava_tokens.json`
- `processed_events.json`

Those files remain ignored by Git and should not be used as production storage. Sent-message persistence is skipped gracefully without `DATABASE_URL` and logs a safe warning.

### 6.4 Twilio WhatsApp 24-hour/freeform window

Freeform WhatsApp messages can fail outside the allowed WhatsApp customer service window.

Observed error:

```text
63016 - Failed to send freeform message because you are outside the allowed window.
```

Current workaround:

- Send a message manually from the phone to the Twilio WhatsApp number to reopen the window.
- Then retry/resend as needed.

Future fix:

- Use approved WhatsApp message templates for business-initiated outbound messages.

### 6.5 Delivery status tracking is initial

The app stores Twilio Message SID metadata and can update status through `/webhook/twilio/status` after Twilio is configured to call that URL.

Remaining work:

- configure the Twilio status callback in Twilio Console or API
- use tracked status for retry decisions
- add approved templates for out-of-window delivery
- add richer message history views or recovery tooling if needed

### 6.6 Current active issue

```text
ISSUE-001 - AI feedback misclassifies steady-pace rides as interval sessions
```

See `docs/ISSUE_TRACKER.md` before changing ride classification or AI prompts.

## 7. Important commands

Run tests:

```bash
python -m unittest discover
```

Run compile validation:

```bash
python -m compileall app scripts
```

Run locally:

```bash
uvicorn app.main:app --reload
```

Production start command through Procfile:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required database variable for Railway/Supabase-backed persistence:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Check Railway health:

```text
https://web-production-d4872.up.railway.app/health
```

Twilio delivery status callback URL:

```text
https://web-production-d4872.up.railway.app/webhook/twilio/status
```

## 8. Recommended next milestone

The next recommended milestone is reliability hardening now that basic owner routing exists.

Suggested order:

1. Confirm deployed OAuth callback maps the current Strava athlete to `app_users`.
2. Confirm one real Strava webhook with `owner_id` uses the mapped user, token, and WhatsApp destination.
3. Configure Twilio status callbacks to call `/webhook/twilio/status` if not already done.
4. Fix `ISSUE-001` by refining ride intensity classification rules for steady rides with minor hills.
5. Use sent-message status for retry/recovery decisions.
6. Add approved WhatsApp templates for out-of-window messages.
7. Add explicit onboarding UI or WhatsApp-command flow.
