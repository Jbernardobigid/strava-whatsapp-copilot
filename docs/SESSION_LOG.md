# TrainingBuddy Session Log

This file records major project sessions and decisions.

## 2026-04-22 — Initial webhook and WhatsApp automation

- Confirmed Strava app was created.
- Confirmed Twilio WhatsApp Sandbox was joined.
- Built local FastAPI app.
- Added `/health` endpoint.
- Added `/test-whatsapp` endpoint.
- Connected Strava OAuth.
- Fetched Strava activities.
- Sent latest activity to WhatsApp.
- Updated messages to Brazilian Portuguese.
- Improved duration formatting from decimal minutes to `1h 17min` style.
- Added Strava token persistence.
- Created GitHub repository.
- Added `requirements.txt` and README.

## 2026-04-22 — Strava webhooks

- Set up ngrok for local webhook testing.
- Added `GET /webhook/strava` verification endpoint.
- Fixed FastAPI query alias issue for dotted Strava params:
  - `hub.mode`
  - `hub.challenge`
  - `hub.verify_token`
- Created Strava webhook subscription.
- Confirmed live webhook event arrived.
- Confirmed WhatsApp message sent automatically after Strava activity creation.

## 2026-04-22 — Exact activity fetch

- Replaced “fetch latest activity” logic with exact activity fetch using webhook `object_id`.
- Added `get_strava_activity_by_id(activity_id)`.
- Fixed syntax/indentation issues during update.
- Confirmed object ID version worked.

## 2026-04-22 — Weekly context

- Added recent activity fetch.
- Added weekly context calculation.
- Added comparison against previous 7 days.
- Added `/debug/weekly-context` endpoint.
- Fixed bug where weekly context returned `(summary, metrics)` but message builder expected `(summary, error)`.
- Rebuilt `main.py` with cleaner weekly context shape.
- Added PT-BR date formatting.

## 2026-04-22 — Duplicate protection

- Observed Strava sending duplicate webhook events for the same activity.
- Added `processed_events.json`.
- Added deduplication key.
- Initially included `event_time`, which failed because duplicate deliveries had different event times.
- Fixed key to use:

```text
object_type:aspect_type:object_id
```

- Confirmed duplicate webhook events are now ignored.

## 2026-04-23 — Message polish

- Added PT-BR number formatting.
- Added ride title logic.
- Added weekly load warning for high weekly volume.
- Improved next-day suggestion.
- Added activity name normalization:
  - Morning Ride → Pedalada matinal
  - Afternoon Ride → Pedalada da tarde
  - Evening Ride → Pedalada noturna

## 2026-04-23 — Modular refactor

- Decided that `main.py` had grown too large.
- Refactored into modular structure:
  - `app/routes`
  - `app/services`
  - `app/utils`
  - `app/config.py`
- Changed run command to:

```bash
uvicorn app.main:app --reload
```

- Renamed old root `main.py` to legacy file.
- Confirmed endpoints still worked after refactor.
- Confirmed webhook still worked after refactor.

## 2026-04-23 — Recovery tooling

- Added `scripts/recover_missed_activities.py`.
- Recovery script fetches recent activities and sends missed rides.
- Confirmed script recovered an activity.
- Discovered Twilio WhatsApp window issue causing undelivered messages.
- Used manual resend by activity ID after reopening WhatsApp window.

## 2026-04-24 — Documentation

- Created product documentation DOCX.
- Included overview, sales pitch, MVP, technical architecture, roadmap, and next steps.

## 2026-04-24 — Logging

- Added central logger at `app/utils/logger.py`.
- Added `logs/app.log` with rotation.
- Added logging to:
  - app startup
  - webhook route
  - WhatsApp service
  - Strava service
  - recovery script
- Confirmed logs are written locally.
- Decided to keep one shared log file for now.

## 2026-04-24 — AI v1

- Added OpenAI integration.
- Added AI service for training interpretation.
- Kept deterministic fallback.
- Tuned prompt for Brazilian Portuguese, concise coaching interpretation.
- Reduced generic motivational language.
- Separated AI responsibility from system formatting/business logic.

## 2026-04-24 — Improved activity intelligence

- Exported full Strava activity JSON for analysis.
- Discovered that distance/elevation/time alone misclassified an intense interval ride as easy.
- Updated `simplify_activity()` to include:
  - average watts
  - weighted average watts
  - max watts
  - HR metrics
  - suffer score
  - PR count
  - achievements
  - laps
- Updated `classify_ride()` to detect interval-like sessions.
- Added `intervalado` classification.
- Updated title to `Treino intervalado 🔥`.
- Updated next-day suggestion for interval sessions.
- Confirmed AI interpretation now aligns with interval classification.

## 2026-04-24 — Railway deployment

- Created Procfile:

```text
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Deployed app to Railway.
- Confirmed deployment online.
- Updated Strava webhook subscription to Railway URL.
- Current observed subscription:

```text
id: 342486
callback_url: https://web-production-d4872.up.railway.app/webhook/strava
```

- Updated Strava Authorization Callback Domain to:

```text
web-production-d4872.up.railway.app
```

- Updated Railway `STRAVA_REDIRECT_URI` to:

```text
https://web-production-d4872.up.railway.app/strava/callback
```

## 2026-04-30 — Repository hygiene cleanup

- Removed tracked `processed_events.json` from the repository while keeping the runtime filename ignored.
- Added explicit ignore patterns for SSH/private key files.
- Standardized the raw activity export helper path to `scripts/export_activity_json.py`.
- Updated project documentation to use the standardized script path.

## 2026-04-30 — Supabase PostgreSQL duplicate persistence

- Added SQLAlchemy database setup configured by `DATABASE_URL`.
- Added a `processed_events` table model with a unique constraint on Strava object ID, object type, and aspect type.
- Replaced `processed_events.json` duplicate tracking with database-backed helper functions.
- Updated the recovery script to use the same database duplicate tracking path.
- Added unit coverage for repeated Strava events so duplicate deliveries are only recorded once.

## Next session recommended starting point

1. Check Railway health endpoint:

```text
https://web-production-d4872.up.railway.app/health
```

2. Confirm one real Strava activity hits Railway logs.

3. Confirm WhatsApp delivery from deployed app.

4. Continue persistence hardening:

```text
strava_tokens.json → database or secure Railway variable
sent message state → database
Twilio status callback → database update
```
