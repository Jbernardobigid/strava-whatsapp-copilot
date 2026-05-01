# Context Handoff

_Last updated: 2026-05-01_

This document is a concise handoff for a new ChatGPT/Codex session working on TrainingBuddy, also called Strava WhatsApp Copilot.

## First Things To Read

Start every new task by reading:

```text
AGENTS.md
docs/CONTEXT_HANDOFF.md
docs/PROJECT_STATE.md
```

For planning or triage work, also check:

```text
docs/ISSUE_TRACKER.md
plans/FEATURE_PLANNING_TEMPLATE.md
```

Project-specific rules to preserve:

- Do not expose, print, return, log, or commit secrets.
- WhatsApp messages must be in Brazilian Portuguese.
- Do not remove OpenAI fallback behavior.
- Do not break Strava webhook verification.
- Do not break duplicate protection.
- Do not commit `.env`, token files, processed-event files, activity exports, logs, SSH keys, or API keys.

## App Purpose

TrainingBuddy is a personal cycling copilot. It receives Strava activity webhook events, fetches the full activity, builds a Brazilian Portuguese training interpretation, and sends it through Twilio WhatsApp.

The product still behaves as a one-user MVP by default, but OAuth and webhook processing now support explicit Strava athlete-to-user mapping.

## Deployment Status

The app is deployed on Railway as a FastAPI service.

Production base URL:

```text
https://web-production-d4872.up.railway.app
```

Health check:

```text
https://web-production-d4872.up.railway.app/health
```

Expected response:

```json
{"status":"ok"}
```

Production start command is defined by the Procfile:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Strava Status

Webhook callback URL:

```text
https://web-production-d4872.up.railway.app/webhook/strava
```

Webhook subscription status:

- Strava webhook verification is implemented and must not be broken.
- The webhook is documented as pointing to the Railway URL.
- The subscription ID observed during setup was `342486`.
- Duplicate webhook protection is database-backed when `DATABASE_URL` is configured.

OAuth and owner-routing status:

- `/connect-strava` redirects directly to Strava authorization.
- `/strava/callback` exchanges the code, stores tokens, and associates the returned Strava `athlete_id` with an `app_users` row.
- Webhook `owner_id` is resolved against `app_users.strava_athlete_id`.
- Resolved users are used for token lookup, WhatsApp destination routing, `processed_events.user_id`, and `sent_messages.user_id`.
- Unknown webhook owners are skipped gracefully with a safe warning instead of using another user's token or destination.
- `/debug/strava-token-status` returns safe metadata only and must not return token values.

## Twilio Status

Twilio WhatsApp sending is implemented and working at the API acceptance level.

Current delivery tracking status:

- Sent-message metadata is persisted in the `sent_messages` table when `DATABASE_URL` is configured.
- Destination WhatsApp numbers are stored masked, not raw.
- `POST /webhook/twilio/status` receives Twilio delivery status callbacks and updates rows by `MessageSid`.
- The callback response returns only safe metadata and does not return tokens, raw phone numbers, or full error message text.
- If `DATABASE_URL` is absent, sent-message persistence is skipped gracefully with a safe warning.

Twilio delivery status callback URL to configure in Twilio:

```text
https://web-production-d4872.up.railway.app/webhook/twilio/status
```

Important limitation:

- A Twilio Message SID means Twilio accepted the message, not that WhatsApp delivered it.
- Freeform WhatsApp messages can fail outside the 24-hour customer service window with error `63016`.
- The current workaround is to send a manual WhatsApp message to the Twilio number to reopen the window.
- The long-term fix is approved WhatsApp templates for out-of-window messages.

Do not expose Twilio auth tokens or WhatsApp phone numbers unless already intentionally masked.

## AI Coaching Status

AI v1 is considered complete.

The AI layer is used only for the short training interpretation under `Leitura do treino:`. Deterministic code still controls activity fetching, ride classification, weekly context, message structure, formatting, next-day suggestion, duplicate handling, and fallback behavior.

Do not remove OpenAI fallback behavior. Do not change WhatsApp message content or AI coaching behavior unless the task explicitly asks for it.

Current known AI/classification issue:

```text
ISSUE-001: AI feedback misclassifies steady-pace rides as interval sessions.
```

See `docs/ISSUE_TRACKER.md` before changing ride classification or AI prompts.

## Database Persistence Status

Production persistence uses Supabase PostgreSQL through `DATABASE_URL`.

When `DATABASE_URL` is configured:

- App users are stored in PostgreSQL.
- Strava tokens are stored per app user in PostgreSQL.
- Processed webhook events are stored in PostgreSQL.
- Twilio sent-message metadata and status are stored in PostgreSQL.
- Tables are initialized safely at startup through SQLAlchemy metadata creation.

When `DATABASE_URL` is not configured:

- Local development falls back to ignored JSON runtime files for Strava tokens and processed events.
- `strava_tokens.json` is used for local token fallback.
- `processed_events.json` is used for local processed-event fallback.
- `sent_messages` persistence is skipped gracefully.

The JSON fallback is for local development only and should not be treated as production storage.

## Current Database-Backed Tables And Features

Current SQLAlchemy tables:

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

sent_messages
- id
- user_id
- strava_activity_id
- twilio_message_sid
- to_number
- status
- error_code
- error_message
- created_at
- updated_at
```

Current database-backed features:

- Default app user creation/lookup.
- App user lookup by Strava athlete ID.
- Strava token persistence per user.
- Token refresh updates the user's database record, including any new refresh token returned by Strava.
- Webhook owner routing by Strava `owner_id`.
- Processed-event duplicate protection.
- `processed_events.user_id` is populated when Strava `owner_id` maps to an app user.
- Current duplicate uniqueness still preserves the existing global event-key behavior.
- Twilio sent-message metadata persistence after Twilio accepts a send.
- `sent_messages.user_id` and `sent_messages.strava_activity_id` are populated when webhook owner routing resolves a user.
- Twilio delivery status updates by Message SID.

Do not print, log, return, or commit token values.

## Current Planning And Tracking Docs

Issue tracker:

```text
docs/ISSUE_TRACKER.md
```

Current active issue:

```text
ISSUE-001 - AI feedback misclassifies steady-pace rides as interval sessions
Status: open
Priority: Medium (P2)
Target resolution: 2026-05-31
```

Feature planning template:

```text
plans/FEATURE_PLANNING_TEMPLATE.md
```

The template now includes backlog seeds for:

- Strava activity tags.
- Refined AI coach.
- Multiple AI coach personalities.
- Sponsored follow-up messages.

## Remaining Known Limitations

- The product is still a one-user MVP despite multi-user-ready tables and owner routing.
- There is no explicit onboarding UI or WhatsApp-command onboarding flow yet.
- WhatsApp number verification is not fully built yet.
- WhatsApp destination routing is still basic and uses the existing configured/default destination for current users.
- Duplicate protection is not fully user-scoped yet.
- Twilio status callback must be configured in Twilio for delivery updates to arrive.
- Twilio delivery tracking is initial and is not yet used for retries or recovery decisions.
- There is no activities table yet.
- There is no approved WhatsApp template flow yet.
- Freeform WhatsApp messages can fail outside the 24-hour window.
- Local JSON fallback remains for development when `DATABASE_URL` is absent.
- Ride classification currently has an open trust issue for steady rides being labeled as interval sessions.

## Next Recommended Tasks

Recommended order:

1. Confirm deployed OAuth callback maps the current Strava athlete to `app_users`.
2. Confirm one real Strava webhook with `owner_id` uses the mapped user, token, and WhatsApp destination.
3. Configure Twilio status callbacks to call `/webhook/twilio/status` if not already done.
4. Fix `ISSUE-001` by refining ride intensity classification rules for steady rides with minor hills.
5. Use sent-message status for retry/recovery decisions.
6. Add approved WhatsApp templates for out-of-window messages.
7. Add explicit onboarding UI or WhatsApp-command flow.
8. Make duplicate protection fully user-scoped after owner routing is mature.
9. Optionally add `activities` persistence for raw Strava activity snapshots and analysis history.

## Important Commands

Run validation:

```bash
python -m compileall app scripts
python -m unittest discover
```

Run locally:

```bash
uvicorn app.main:app --reload
```

Local health check:

```text
http://127.0.0.1:8000/health
```

Production health check:

```text
https://web-production-d4872.up.railway.app/health
```

Connect Strava in production:

```text
https://web-production-d4872.up.railway.app/connect-strava
```

Safe Strava token metadata check:

```text
https://web-production-d4872.up.railway.app/debug/strava-token-status
```

Twilio delivery status callback URL:

```text
https://web-production-d4872.up.railway.app/webhook/twilio/status
```

Export raw activity JSON locally:

```bash
python scripts/export_activity_json.py ACTIVITY_ID
```

Recover missed activities:

```bash
python scripts/recover_missed_activities.py 10
```

List Strava webhook subscriptions, using placeholders only:

```powershell
curl.exe -G "https://www.strava.com/api/v3/push_subscriptions" `
  -d "client_id=YOUR_CLIENT_ID" `
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## Files That Should Never Be Committed

Do not commit secrets, runtime files, or local exports, including:

```text
.env
strava_tokens.json
processed_events.json
activity_*.json
logs/
TwilioRecoveryCode.txt
stravaauth.txt
railwaykey*
id_ed25519
id_ed25519.pub
*.pem
*.key
```

Also never commit API keys, Strava access tokens, Strava refresh tokens, Twilio auth tokens, OpenAI API keys, Supabase credentials, or unmasked WhatsApp phone numbers.
