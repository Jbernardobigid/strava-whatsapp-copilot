# TrainingBuddy Roadmap

_Last updated: 2026-04-30_

This roadmap organizes future work by priority and maturity.

## Phase 0 — Completed MVP

Status: completed.

Included:

- Local FastAPI app
- Strava OAuth
- Twilio WhatsApp message sending
- PT-BR ride summary
- Strava webhook verification
- Strava webhook activity trigger
- Exact activity fetch by `object_id`
- Duplicate protection
- Recovery script
- Manual resend flow
- Modular app refactor
- Logging
- AI-generated training interpretation
- Improved classification with HR/power/laps
- Railway deployment
- Strava webhook pointed to Railway
- Repository hygiene cleanup for ignored runtime files
- PostgreSQL-backed `processed_events`
- PostgreSQL-backed Strava token persistence when `DATABASE_URL` is configured
- Local JSON fallback only when `DATABASE_URL` is absent

## Phase 1 — Production stabilization

Goal: make the current one-user app reliable enough for daily use.

### 1.1 Persistent storage

Current database-backed tables:

```text
app_users
strava_tokens
processed_events
```

Local fallback files remain for development only:

```text
strava_tokens.json
processed_events.json
```

Recommended next tables:

```text
sent_messages
activities
```

### 1.2 Twilio status callbacks

Add an endpoint like:

```text
POST /webhook/twilio/status
```

Track message state:

- queued
- sent
- delivered
- undelivered
- failed

This solves the problem where Twilio accepts a message but WhatsApp later rejects it.

### 1.3 Safer message processing

Add try/except around webhook processing.

Goal:

- avoid full 500 errors
- log failures
- decide what should be retried

### 1.4 Deployment health monitoring

Add simple operational checks:

- `/health`
- `/debug/weekly-context`
- optional `/debug/config-status`

Do not expose secrets.

## Phase 2 — AI/product quality improvements

Goal: make the assistant feel more useful and personalized.

### 2.1 Prompt tuning

Continue refining AI output to avoid:

- generic fitness language
- motivational clichés
- repeated metrics
- overly long explanations

### 2.2 Variation engine

Avoid repeated phrasing over time.

Examples:

- rotate opening patterns
- avoid always saying “Treino exigente...”
- keep tone consistent but less repetitive

### 2.3 More robust intensity scoring

Create an internal intensity score using:

- weighted watts
- max watts
- average HR
- max HR
- suffer score
- lap intensity
- PR/achievement count

Possible output:

```text
intensity_score: 0-100
intensity_label: leve/moderado/exigente/intervalado
```

### 2.4 FTP-aware classification

User known FTP:

```text
257 W
```

Possible improvements:

- compare weighted watts to FTP
- identify sweet spot / threshold-like sessions
- identify recovery rides
- classify intervals more accurately

### 2.5 Better weekly load

Current weekly context uses count and distance.

Improve with:

- weekly moving time
- weekly elevation
- weekly intensity count
- weekly weighted power if available

## Phase 3 — WhatsApp production hardening

Goal: make WhatsApp delivery reliable.

### 3.1 WhatsApp templates

Create approved WhatsApp templates for out-of-window messages.

This fixes Twilio error 63016.

### 3.2 Message delivery state

Use Twilio callbacks and store message status in database.

### 3.3 Retry queue

If a message fails:

- store failed attempt
- retry later if allowed
- avoid marking as fully delivered too early

## Phase 4 — Multi-user product

Goal: evolve from personal tool to product.

### 4.1 User model

Initial `app_users` table exists with:

- user ID
- label/name
- Strava athlete ID
- WhatsApp number

Future improvements:

- preferred language
- timezone
- training preferences

### 4.2 Per-user tokens

Initial `strava_tokens` table exists and stores one token row per default user.

Future improvements:

- explicit user onboarding
- multiple users
- owner/user lookup during webhook processing

### 4.3 Per-user processed events

`processed_events.user_id` can be stored when Strava `owner_id` maps to an app user.

Future deduplication should include user/athlete context after onboarding exists.

Example future key:

```text
athlete_id:activity:create:activity_id
```

### 4.4 Onboarding flow

Needed steps:

1. Connect Strava.
2. Confirm WhatsApp number.
3. Send test message.
4. Start receiving activity messages.

## Phase 5 — Content engine

Goal: turn ride analysis into social content.

Possible features:

- Instagram caption generation
- Strava post comments
- weekly cycling recap
- image/story generation
- brand-aligned content for cycling apparel/community

## Phase 6 — Analytics dashboard

Goal: provide visual history.

Possible dashboard metrics:

- rides per week
- distance per week
- time per week
- elevation per week
- intensity distribution
- interval sessions
- recovery days
- AI message history

## Recommended immediate next step

The strongest next engineering step is:

```text
Add Twilio status callbacks and sent message persistence.
```

Reason:

- Twilio acceptance does not guarantee WhatsApp delivery
- retry behavior needs durable state
- this is the next reliability bottleneck after token and duplicate persistence

Suggested next order:

1. Add Twilio status callback.
2. Store sent messages.
3. Store message delivery state.
4. Add explicit onboarding.
5. Make duplicate protection fully user-scoped.
