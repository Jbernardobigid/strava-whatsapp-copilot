# Planned Features

This document tracks future TrainingBuddy product ideas that are not implemented yet. Use `plans/FEATURE_PLANNING_TEMPLATE.md` when turning any item here into a standalone implementation plan.

Keep this register high-signal and future-facing. Do not document secrets, raw phone numbers, tokens, or private exports here.

## Feature Register

| ID | Feature | Status | Primary purpose | Suggested next step |
|---:|---|---|---|---|
| 1 | Strava Activity Tags | Planned | Capture rider intent from activity labels or tags. | Define the first supported tag vocabulary. |
| 2 | Refined AI Coach | Planned | Improve AI interpretation quality while keeping deterministic app logic in control. | Document desired voice and anti-patterns. |
| 3 | Multiple AI Coach Personalities | Planned | Let users choose coaching style without changing ride analysis. | Define allowed personality keys and tone rules. |
| 4 | Sponsored Follow-Up Messages | Planned | Create an opt-in monetization channel separated from core coaching. | Define consent policy and sponsor boundaries. |
| 5 | User Groups / Audience Segmentation | Planned | Organize users into product-safe groups for analytics, campaigns, and future personalization. | Define allowed group types and privacy rules. |

## 1. Strava Activity Tags

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

## 2. Refined AI Coach

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

## 3. Multiple AI Coach Personalities

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

## 4. Sponsored Follow-Up Messages

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

## 5. User Groups / Audience Segmentation

**Feature name:**

User Groups / Audience Segmentation.

**Purpose:**

Plan a future capability for assigning TrainingBuddy users to one or more product-safe groups or audience segments. The goal is to support more relevant product experiences, cohort analytics, future subscription tiers, and business opportunities such as targeted partner campaigns without changing current coaching behavior immediately.

**Problem it solves:**

As TrainingBuddy moves from a one-user MVP toward multi-user onboarding, treating every user as the same audience will limit product learning and monetization. Without segmentation, the product cannot easily support targeted communication, partner campaign eligibility, cohort analysis, user-specific experiences, or revenue experiments.

Sponsors and partners usually want to reach specific audiences rather than every user. Product-safe grouping would make it possible to plan relevant campaigns and experiences while avoiding sensitive or discriminatory segmentation.

**Example groups:**

- Beginner riders.
- Endurance-focused riders.
- High-volume riders.
- Low-frequency riders.
- Commuters.
- Race-focused riders.
- Users interested in nutrition content.
- Users eligible for sponsored hydration messages.
- Highly engaged users.
- Inactive users.
- Free tier users.
- Premium tier users.

**Technical or architectural changes needed:**

Possible future changes, not for the current documentation-only task:

- `app/models.py`: add passive tables such as `user_groups`, `user_group_memberships`, or `audience_segments`.
- `app/services/`: add a service for assigning, updating, and evaluating user groups.
- `app/routes/`: add internal/admin endpoints for viewing or assigning groups once admin safety is defined.
- `app/utils/`: add helper functions for safe masking, group-rule evaluation, and privacy-preserving debug output.
- `docs/`: document allowed segmentation rules, privacy constraints, consent boundaries, and examples of disallowed attributes.

Possible future `user_groups` fields:

- `id`
- `name`
- `description`
- `group_type`
- `is_active`
- `created_at`
- `updated_at`

Possible future `user_group_memberships` fields:

- `id`
- `user_id`
- `group_id`
- `source`
- `reason`
- `created_at`
- `updated_at`

Optional later campaign-related tables:

- `campaigns`
- `campaign_audience_rules`
- `campaign_deliveries`

**Behavior changes:**

There should be no immediate application behavior change until this feature is implemented in a later task. Current WhatsApp message content, AI coaching behavior, Strava webhook behavior, duplicate protection, and database models should remain unchanged for now.

Future behavior could include:

- Selecting which sponsored follow-up message a user is eligible to receive.
- Choosing different onboarding flows by user type.
- Analyzing retention by user group.
- Enabling partner campaigns only for relevant groups.
- Supporting premium and free user experiences.

**Risks and constraints:**

- Privacy concerns if grouping rules are too broad, opaque, or personal.
- Over-targeting users or making the product feel spammy.
- Sending irrelevant sponsored messages that reduce trust.
- Accidentally using sensitive or protected attributes.
- Confusing group logic with AI coaching logic.
- Making the data model too complex before the multi-user product needs it.

Segmentation should use explicit user choices, product behavior, subscription status, or activity metadata. It should not use sensitive personal attributes such as race, ethnicity, religion, health status, political views, or similar protected characteristics.

**Testing plan:**

Future validation should include:

- Unit tests for group assignment and rule evaluation logic.
- Tests confirming users can belong to multiple groups.
- Tests confirming inactive groups are ignored.
- Tests confirming unknown users fall back safely.
- Tests confirming sponsored campaigns only target eligible groups.
- Tests confirming debug/admin outputs do not expose private data unnecessarily.

**Open questions:**

- Should groups be manually assigned, automatically inferred, or both?
- Should users be able to opt out of sponsored content?
- Which group types are safe and useful for the MVP?
- Should group membership be visible to users?
- How will sponsored messages respect WhatsApp opt-in and template requirements?
- Should group logic affect AI coaching, sponsored messages only, or both?
- Should the product start with simple static groups before adding rule-based segmentation?

**Recommended implementation order:**

1. Define allowed group types and privacy rules.
2. Add a passive data model for groups and memberships.
3. Add internal-only tools to assign users to groups.
4. Add tests for group lookup and fallback behavior.
5. Use groups only for analytics first.
6. Later connect groups to sponsored follow-up eligibility.
7. Later connect groups to personalization or subscription features.
