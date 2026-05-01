# Feature Planning Template

Use this template to plan future TrainingBuddy features before implementation. Copy this file into a new feature plan, rename it with a short descriptive filename, and fill in the sections before changing application behavior.

Recommended filename pattern:

```text
plans/YYYY-MM-DD-feature-name.md
```

## 1. Feature Name And Purpose

**Feature name:**

[Short, clear name for the feature.]

**Purpose:**

[One or two sentences explaining what this feature is meant to do.]

**Target user:**

[Who benefits from this feature? For the current MVP, specify whether this is for the default one-user flow or future multi-user behavior.]

**Expected outcome:**

[What should become better, easier, safer, more reliable, or more useful once this exists?]

**Non-goals:**

[What this feature intentionally will not do in this iteration.]

## 2. Problem It Solves

**Current problem:**

[Describe the pain point, reliability gap, product limitation, or operational issue.]

**Why it matters:**

[Explain the impact on the user, product quality, reliability, growth, or operations.]

**Current workaround:**

[Describe how this is handled today, if there is a workaround.]

**Success criteria:**

- [Observable or measurable outcome]
- [Another success signal]
- [Optional third success signal]

## 3. User Experience And Behavior

**User-facing behavior:**

[What the user sees, receives, clicks, configures, or notices.]

**System behavior:**

[What the app should do behind the scenes.]

**Behavior that must remain unchanged:**

- WhatsApp message content stays unchanged unless the feature explicitly requires a content change.
- AI coaching behavior and fallback stay unchanged unless the feature explicitly requires a coaching change.
- Strava webhook verification must not break.
- Duplicate event protection must not break.
- Secrets, token values, and raw phone numbers must not be exposed.

## 4. Technical Or Architectural Changes Needed

**Affected areas:**

- `app/routes/`: [New or changed endpoints]
- `app/services/`: [Business logic, Strava, Twilio, OpenAI, or coaching changes]
- `app/utils/`: [Formatting, logging, persistence, shared helpers]
- `app/models.py`: [Database model changes]
- `app/database.py`: [Database initialization or migration considerations]
- `scripts/`: [Operational, recovery, backfill, or export scripts]
- `docs/`: [Runbook, architecture, project state, session log updates]
- `tests/`: [New or updated test coverage]

**Data model changes:**

[New tables, columns, indexes, constraints, relationships, or migration/backfill needs.]

**External integrations:**

[Strava, Twilio, OpenAI, Supabase, Railway, or other provider changes. Include manual console settings if needed.]

**Environment variables:**

[New or changed env vars. Use placeholders only. Do not include real secrets.]

**Fallback behavior:**

[How the feature behaves when optional services or `DATABASE_URL` are unavailable.]

## 5. Security And Privacy

**Sensitive data involved:**

[Tokens, phone numbers, activity data, user identifiers, message bodies, etc.]

**Storage rules:**

[Whether data is stored, masked, hashed, or avoided entirely.]

**Logging rules:**

[What can be safely logged and what must never be logged.]

**Files that must not be committed:**

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

## 6. Test Plan

**Unit tests:**

- [Core function or model behavior]
- [Error/fallback behavior]
- [Security/privacy assertion]

**Integration or route tests:**

- [Endpoint or webhook behavior]
- [Persistence behavior]
- [External callback payload shape]

**Manual validation:**

- [Railway health check]
- [Strava/Twilio/Supabase console step]
- [One real or simulated end-to-end check]

**Required commands:**

```bash
python -m compileall app scripts
python -m unittest discover
```

## 7. Deployment And Operations

**Deployment notes:**

[Railway, Supabase, Twilio, Strava, or other operational steps.]

**Rollback plan:**

[How to disable or revert the feature safely.]

**Monitoring:**

[Logs, status endpoints, database checks, provider dashboards, or alerts to watch after release.]

## 8. Risks And Open Questions

**Risks:**

- [Risk 1]
- [Risk 2]
- [Risk 3]

**Open questions:**

- [Question 1]
- [Question 2]
- [Question 3]

## 9. Recommended Implementation Order

1. Confirm current behavior and relevant docs.
2. Add or update tests for the intended behavior.
3. Make the smallest code or documentation change that supports the feature.
4. Run validation commands.
5. Update docs and session log.
6. Deploy or document manual configuration steps.
7. Verify the feature in production or with a safe local simulation.

## 10. Final Handoff Notes

**Files changed:**

- [File path]
- [File path]

**Validation results:**

[Record compile/test/manual validation results.]

**Manual follow-up:**

[Any Railway, Twilio, Strava, or Supabase action still required.]

# Planned Feature Backlog Seeds

The sections below are concrete planning seeds for near-future TrainingBuddy features. Each can be copied into a standalone dated plan under `plans/` before implementation.

## A. Strava Activity Tags

**Feature name:**

Strava activity tags for training context.

**Purpose:**

Allow TrainingBuddy to recognize activity-level tags such as `treino`, `prova`, `recuperacao`, `intervalado`, or `longao` so messages and future analytics can understand the rider's intent, not just the raw metrics.

**Problem it solves:**

The app currently infers ride type mostly from Strava metrics. A race-like effort, structured workout, social ride, or recovery spin may be misread if the metrics do not tell the full story. User-provided tags would give the system explicit intent and reduce wrong assumptions.

**Technical needs:**

- Decide the source of tags: Strava activity title markers, description hashtags, manual database labels, or a future WhatsApp command.
- Add a tag parser in `app/services/strava_service.py` or a dedicated helper in `app/utils/`.
- Consider an `activity_tags` table or a `tags` JSON/text column if activity persistence is added.
- Keep webhook processing unchanged except for optional enrichment after the activity is fetched.
- Add deterministic tests for tag extraction from names/descriptions.
- Make tags available to `coaching_service` without changing the current WhatsApp format until a content change is explicitly planned.

**Open questions:**

- Should tags be inferred from Strava names like `[prova] Gran Fondo` or hashtags like `#prova`?
- Should users be able to correct tags after the ride through WhatsApp?
- Which tags should influence ride classification versus only analytics?
- Should tags be stored before the app has a durable `activities` table?

**Implementation order:**

1. Define the first supported tag vocabulary and matching rules.
2. Add pure parsing helpers and unit tests.
3. Thread parsed tags into simplified activity data without changing message text.
4. Optionally persist tags when activity persistence exists.
5. Update docs and add examples for supported tag formats.

## B. Refined AI Coach

**Feature name:**

Refined AI coach interpretation.

**Purpose:**

Improve the quality, specificity, and consistency of the AI-generated `Leitura do treino:` section while keeping deterministic business logic in control of workflow, structure, and safety fallback.

**Problem it solves:**

The current AI layer works, but future messages may still sound generic, repeat phrasing, overstate conclusions, or miss rider-specific training context. Better prompt design and stricter model inputs can make the coaching feel more useful without giving the AI control over the app.

**Technical needs:**

- Refine prompts in `app/services/ai_service.py` with clearer style constraints and examples.
- Pass structured context only: ride classification, key metrics, recent-week summary, optional tags, and known constraints.
- Keep deterministic fallback if OpenAI fails.
- Keep WhatsApp body assembly in `coaching_service` so AI only writes the interpretation segment.
- Consider model configuration changes through `OPENAI_MODEL`, but keep a safe default.
- Add tests for fallback behavior and prompt/input shaping where practical.
- Add golden examples for expected tone without snapshotting brittle full AI outputs.

**Open questions:**

- Should the coach mention power/heart-rate details directly, or only interpret them?
- Should the AI adapt based on training phase, fatigue, or user goals once those exist?
- Which model is the best cost/quality fit for short PT-BR coaching text?
- Should the app store AI outputs for future repetition avoidance?

**Implementation order:**

1. Document desired voice and anti-patterns.
2. Refine `ai_service` prompt and input payload.
3. Add tests that confirm fallback remains available and no workflow logic moves into AI.
4. Run validation and compare outputs manually with representative activities.
5. Update `docs/PROJECT_STATE.md` and session notes with any prompt/model changes.

## C. Multiple AI Coach Personalities

**Feature name:**

Selectable AI coach personalities.

**Purpose:**

Let users choose the coaching style that best fits how they want to receive feedback, while preserving the same underlying ride analysis and safety constraints.

**Problem it solves:**

A single coaching tone may not fit every moment or user. Some users want direct performance critique, some want calm recovery guidance, and others prefer a friendlier motivational tone. Personalities can increase perceived usefulness without changing the core training logic.

**Coach styles:**

- `direto`: concise, objective, performance-focused, low fluff.
- `motivador`: encouraging, energetic, still specific to the ride.
- `tecnico`: more analytical, mentions power, heart rate, load, and patterns when available.
- `leve`: casual and supportive, useful for recovery or social rides.

**User experience:**

The current one-user MVP can start with a default personality configured in code or an environment variable. Later, multi-user support can store `coach_personality` per user and let users change it through onboarding, a settings page, or a WhatsApp command.

**Technical needs:**

- Add a personality enum/config map in `ai_service` or a dedicated coaching config module.
- Keep deterministic ride classification unchanged.
- Pass selected personality into AI prompt construction.
- Add optional `coach_personality` to `app_users` when user preferences are ready.
- Avoid changing message structure; personality should affect only the AI interpretation text unless explicitly planned.
- Add tests that each personality maps to expected prompt instructions.

**Open questions:**

- Should personality be global for the MVP or stored per user now?
- Should users be able to switch personality through WhatsApp commands?
- Should certain ride tags force a style, such as `prova` using `tecnico`?
- How do we prevent playful styles from becoming generic or too long?

**Implementation order:**

1. Define allowed personality keys and tone rules.
2. Add prompt-instruction mapping with a default personality.
3. Add tests for personality selection and fallback to default.
4. Optionally add a user preference column after onboarding direction is clear.
5. Update docs with available personalities and examples.

## D. Sponsored Follow-Up Messages

**Feature name:**

Sponsored follow-up messages.

**Purpose:**

Create an opt-in business channel for occasional sponsor or partner follow-up messages that are relevant to the rider's activity context, while keeping coaching messages trustworthy and clearly separated from ads.

**Problem it solves:**

TrainingBuddy may need a monetization path, but inserting sponsor content directly into the core coaching message could reduce trust. A separate, consent-based follow-up message creates a cleaner business model and gives users control.

**Business logic:**

Sponsored messages should be sent only when all conditions are true:

- The user has explicitly opted in.
- The sponsor campaign is active.
- The ride context matches campaign rules, such as long ride, race, recovery, or tag-based criteria.
- Frequency caps are respected.
- WhatsApp policy and Twilio template requirements are satisfied.
- The message is clearly distinguishable from coaching.

**User consent:**

Start with no sponsored messages by default. Store explicit opt-in state, opt-in timestamp, and opt-out state. Every sponsored flow should have a simple opt-out path. Do not infer consent from normal app usage.

**Technical needs:**

- Add user consent fields or a dedicated `user_preferences` table.
- Add campaign models such as `sponsor_campaigns` and `sponsored_message_events` when ready.
- Use `sent_messages` or a related table to track sponsored delivery attempts and frequency caps.
- Add Twilio template support for business-initiated sponsored messages outside the WhatsApp window.
- Keep sponsor logic outside `coaching_service` so coaching remains independent.
- Add eligibility checks in a dedicated service, for example `app/services/sponsor_service.py`.
- Add tests for opt-in, opt-out, frequency caps, campaign matching, and no-send defaults.

**Open questions:**

- What sponsor categories are acceptable for the product?
- Should sponsored messages be sent after every qualifying ride or batched weekly?
- What is the minimum consent UX before this can launch?
- How should sponsorship be disclosed in Portuguese?
- Should sponsored messages use approved WhatsApp templates from day one?

**Implementation order:**

1. Define consent policy, sponsor boundaries, and disclosure language.
2. Add database fields/tables for consent and campaign tracking.
3. Add eligibility service with no-send defaults.
4. Add tests for consent and frequency caps before any sending code.
5. Integrate Twilio template sending only after policy and templates are ready.
6. Update runbook with opt-out, monitoring, and rollback steps.
