# TrainingBuddy Technical Decisions

_Last updated: 2026-04-24_

This document records important technical/product decisions made during the project.

## Decision 1 — Start with one-file MVP

We initially built the app in a single `main.py`.

Reason:

- faster iteration
- easier learning
- fewer moving parts
- easier debugging during early MVP

Later, once the app worked, this became too crowded.

Final outcome:

- Refactored to modular structure under `app/`.

## Decision 2 — Use FastAPI

FastAPI was selected for the backend.

Reason:

- simple route creation
- easy local development with Uvicorn
- good async support
- straightforward webhook implementation
- good fit for Python learning and API integrations

## Decision 3 — Use Twilio WhatsApp Sandbox first

Twilio Sandbox was used to avoid upfront WhatsApp Business setup complexity.

Reason:

- faster testing
- easy to send messages from Python
- good developer logs
- low friction for MVP

Known tradeoff:

- freeform messages fail outside WhatsApp allowed window
- approved templates are needed later

## Decision 4 — Use Strava webhooks

Webhook-based automation was added after manual activity fetching worked.

Reason:

- event-driven behavior
- no polling required
- more product-like experience

The app now reacts to Strava `activity:create` events.

## Decision 5 — Fetch exact activity by `object_id`

The app originally fetched the latest activity.

Problem:

- if two activities arrived close together, latest activity could be wrong

Decision:

- use webhook `object_id` to fetch exact activity

Outcome:

- safer and more production-like behavior

## Decision 6 — Add deduplication

Strava delivered duplicate webhook events.

Problem:

- the same activity created multiple WhatsApp messages

Decision:

- use deduplication key:

```text
object_type:aspect_type:object_id
```

Example:

```text
activity:create:18236736799
```

Outcome:

- first event processes
- later duplicate deliveries are ignored

## Decision 7 — Use recovery script for missed webhooks

Local computer sleep caused missed events.

Decision:

- create `scripts/recover_missed_activities.py`

Reason:

- simple operational recovery
- no change to main webhook flow
- safe due to deduplication

Outcome:

- missed activities can be recovered on demand

## Decision 8 — Add manual resend by activity ID

Twilio accepted messages that later became undelivered due to WhatsApp window rules.

Problem:

- the activity could be marked processed even though the user did not receive the WhatsApp message

Decision:

- use a manual resend command/script by activity ID

Reason:

- surgical fix
- does not break deduplication state
- avoids editing `processed_events.json`

## Decision 9 — Add logging before AI expansion

Logging was added before expanding AI features.

Reason:

- easier debugging
- better operational visibility
- important before external AI calls

Current approach:

- one shared `logs/app.log`
- logger names identify source module
- rotating file handler

## Decision 10 — Use hybrid AI design

AI was added only for the training interpretation text.

Decision:

- deterministic code handles workflow and classification
- AI generates only the short interpretation
- fallback text exists if OpenAI fails

Reason:

- safer
- more predictable
- avoids letting AI control critical logic

## Decision 11 — Improve classification before improving prompt

The AI initially described an interval workout as easy because the app only provided distance/time/elevation.

Problem:

- simplified activity hid real intensity signals

Decision:

- enrich activity simplification with:
  - power
  - HR
  - suffer score
  - PR count
  - achievements
  - laps

Outcome:

- intense interval rides can now be classified as `intervalado`

## Decision 12 — Deploy to Railway

Railway was selected for deployment.

Reason:

- easy GitHub deployment
- simple env var management
- public URL for Strava webhooks
- no local machine dependency

Tradeoff:

- filesystem is ephemeral
- persistence should be moved to database later

## Decision 13 — Keep one log file for now

Question considered:

- should logs be split by module?

Decision:

- keep one log file: `logs/app.log`

Reason:

- app is still small
- logger names are enough to distinguish source
- simpler operations

Future option:

- split into service-specific logs only if app becomes noisy

## Decision 14 — Do not overbuild multi-user yet

Current app is one-user.

Decision:

- do not add multi-user support yet

Reason:

- validate product behavior first
- avoid premature complexity

Future direction:

- add database-backed users, tokens, WhatsApp numbers, and ownership mapping
