# TrainingBuddy / Strava WhatsApp Copilot — Project State

_Last updated: 2026-04-30_

## 1. Project overview

TrainingBuddy, also referred to as Strava WhatsApp Copilot, is a personal cycling assistant that listens for new Strava activities and sends a WhatsApp message in Brazilian Portuguese with a short training interpretation.

The app currently works as an event-driven workflow:

```text
Strava activity created
        ↓
Strava webhook
        ↓
Railway-hosted FastAPI app
        ↓
Check processed_events in Supabase PostgreSQL
        ↓
Load Strava token for the default app user
        ↓
Fetch full Strava activity by object_id
        ↓
Classify ride using metrics
        ↓
Generate AI-assisted training interpretation
        ↓
Send WhatsApp message through Twilio
        ↓
Record processed event in PostgreSQL
```

The product is currently focused on one user, one Strava account, and one WhatsApp recipient. The database schema now has user and token tables so the current one-user flow can evolve toward multi-user support later.

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

## 3. What is working

The following features are currently working:

- FastAPI app running locally and on Railway.
- Strava OAuth connection.
- Strava token refresh flow.
- Strava webhook verification endpoint.
- Strava webhook subscription pointing to Railway.
- Fetching exact activity by webhook `object_id`.
- WhatsApp sending through Twilio.
- PT-BR message generation.
- Strava token persistence backed by PostgreSQL `app_users` and `strava_tokens` tables when `DATABASE_URL` is configured.
- Local `strava_tokens.json` fallback only when `DATABASE_URL` is not configured.
- Duplicate webhook protection backed by a PostgreSQL `processed_events` table through `DATABASE_URL`.
- Processed events can store `user_id` when Strava `owner_id` maps to the current app user.
- Recovery script for missed activities.
- Manual resend by activity ID.
- Logging to `logs/app.log` locally.
- AI-assisted ride interpretation using OpenAI.
- Improved ride classification using power, heart rate, suffer score, achievements, PR count, and laps.
- Basic unittest coverage for core formatters, activity-name normalization, webhook event keys, ride classification, duplicate event database handling, and database token persistence.
- Repository hygiene cleaned up so runtime files stay untracked, private-key patterns are ignored, and the activity export helper is standardized as `scripts/export_activity_json.py`.

## 4. Current architecture summary

The project was refactored from one large `main.py` into a modular structure:

```text
app/
├── main.py
├── config.py
├── database.py
├── models.py
├── routes/
│   ├── health.py
│   ├── strava.py
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

Database-backed persistence now covers Strava tokens and duplicate webhook protection when `DATABASE_URL` is configured. The app initializes tables safely at startup with SQLAlchemy metadata creation and falls back to local JSON files only for local development without `DATABASE_URL`.

## 5. Current message behavior

A typical WhatsApp message looks like this:

```text
Treino intervalado 🔥

Pedalada matinal
Pedalada • 38,9 km • 1h 17min • 216 m
24/04 às 05:46

Leitura do treino:
Treino exigente, com variações de intensidade que aumentaram bem a carga do pedal.
Dentro de uma semana já consistente, esse tipo de esforço eleva o acúmulo de fadiga.

Seu contexto recente:
4 pedais nos últimos 7 dias • 318,9 km
Em relação aos 7 dias anteriores, seu volume está estável.
Boa carga recente, vale cuidar da recuperação.

Sugestão para amanhã:
Amanhã vale priorizar recuperação ou um giro bem leve.
```

## 6. AI v1 status

AI v1 is considered complete.

The AI layer is used only for the short training interpretation under:

```text
Leitura do treino:
```

The app still uses deterministic code for:

- Activity fetching.
- Ride classification.
- Weekly context calculation.
- Message structure.
- Formatting.
- Next-day suggestion.
- Duplicate handling.

This is intentional. The AI should interpret the ride, not control the workflow.

## 7. Current ride classification logic

The classification now considers more than distance/elevation/time.

Important signals include:

- `average_watts`
- `weighted_average_watts`
- `max_watts`
- `average_heartrate`
- `max_heartrate`
- `suffer_score`
- `achievement_count`
- `pr_count`
- hard laps derived from lap HR/power

The app now supports at least these ride classifications:

- `intervalado`
- `longo`
- `de escalada`
- `moderado`
- `curto`
- `leve`

The classification `intervalado` should take priority when strong intensity signals are present.

## 8. Current known limitations

### 8.1 Persistence is database-backed with local fallback

The app uses PostgreSQL tables configured by `DATABASE_URL` for:

- `app_users`
- `strava_tokens`
- `processed_events`

When `DATABASE_URL` is not configured, local development falls back to:

- `strava_tokens.json`
- `processed_events.json`

Those files remain ignored by Git and should not be used as production storage.

### 8.2 Multi-user behavior is not fully built yet

The schema is multi-user-ready, but the product still behaves as a one-user MVP. The current default-user strategy associates Strava OAuth tokens with a single default app user. Processed events store `user_id` when `owner_id` maps to that user, but duplicate protection still preserves the current global event key behavior.

Future work:

- explicit user onboarding
- owner/user lookup in webhook processing
- per-user WhatsApp destination routing
- user-scoped duplicate uniqueness after onboarding exists

### 8.3 Twilio WhatsApp 24-hour/freeform window

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

### 8.4 Delivery status is not fully tracked

The app currently logs when Twilio accepts a message and returns a SID.

That does not guarantee final WhatsApp delivery.

Future fix:

- Add Twilio status callbacks.
- Track accepted/sent/delivered/undelivered/failed states.

## 9. Important commands

Run tests:

```bash
python -m unittest discover
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

Check local health:

```text
http://127.0.0.1:8000/health
```

Check Railway health:

```text
https://web-production-d4872.up.railway.app/health
```

List Strava webhook subscriptions:

```powershell
curl.exe -G "https://www.strava.com/api/v3/push_subscriptions" `
  -d "client_id=YOUR_CLIENT_ID" `
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## 10. Recommended next milestone

The next recommended milestone is message delivery hardening and true multi-user routing.

Suggested order:

1. Add Twilio status callback endpoint.
2. Track message delivery states.
3. Add sent-message persistence.
4. Add explicit user onboarding.
5. Move duplicate uniqueness to user-scoped behavior after webhook owner routing is explicit.
