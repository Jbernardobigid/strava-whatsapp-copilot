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
