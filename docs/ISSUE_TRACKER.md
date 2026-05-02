# TrainingBuddy Issue Tracker

_Last updated: 2026-05-02_

Use this document to track current product, engineering, operations, and documentation issues for TrainingBuddy / Strava WhatsApp Copilot.

Keep entries concise, actionable, and safe to share. Do not include secrets, token values, raw WhatsApp phone numbers, API keys, or private credentials.

## Status Values

Use one of these values:

- `open`: issue is known and not actively being worked.
- `in progress`: issue is actively being investigated or implemented.
- `blocked`: issue cannot move forward until a dependency or decision is resolved.
- `resolved`: fix or decision is complete.
- `deferred`: intentionally postponed.
- `wontfix`: intentionally not planned.

## Priority Values

Use one of these values:

- `P0`: production outage, data loss, severe security risk, or broken core workflow.
- `P1`: major user-facing issue or reliability risk.
- `P2`: important improvement or non-critical defect.
- `P3`: polish, cleanup, or documentation-only issue.

## Current Issues Summary

| Issue ID | Summary | Status | Priority | Owner/Team | Identified Date | Target Resolution Date |
| --- | --- | --- | --- | --- | --- | --- |
| ISSUE-001 | AI feedback misclassifies steady-pace rides as interval sessions | open | Medium (P2) | Myself (single team member) | 2026-05-01 | 2026-05-31 |

## Active Issues

### Issue ID: ISSUE-001

**Summary:**

AI feedback misclassifies steady-pace rides as interval sessions.

**Status:**

open

**Priority:**

Medium (P2)

**Owner or team:**

Myself (single team member)

**Identified date:**

2026-05-01

**Target resolution date:**

2026-05-31

**Resolved date:**

N/A

**Problem description:**

The AI feedback mislabels steady rides with minor hills as interval training. The likely issue is that ride intensity classification is treating normal terrain-driven pace or effort variation as interval-like structure.

**Impact:**

High. Wrong feedback undermines user trust and product value because the assistant appears to misunderstand the workout type and may give inappropriate recovery or training interpretation.

**Affected areas:**

- `app/services/coaching_service.py`: ride classification rules.
- `app/services/ai_service.py`: AI interpretation may amplify or repeat the incorrect classification.

**Proposed solution or next steps:**

1. Review today's ride data and identify which metrics caused the interval classification.
2. Refine ride intensity classification rules so steady rides with minor hills are not treated as interval sessions.
3. Add or update tests covering steady rides, hilly steady rides, true interval sessions, long rides, and recovery rides.
4. Confirm AI feedback reflects the corrected classification without changing the overall WhatsApp message structure unless explicitly planned.

**Validation plan:**

- Test on various ride types to confirm accurate feedback.
- Include at least one steady-pace ride with minor hills and one true interval session.
- Run `python -m compileall app scripts` and `python -m unittest discover` after implementation.

**Related links or references:**

- Today's ride data.
- `plans/PLANNED_FEATURES.md`, feature `2`: Refined AI Coach.

**Notes:**

This issue tracks the concrete misclassification defect. Broader future AI coach quality work remains in `plans/PLANNED_FEATURES.md` under feature `2`, so the issue tracker stays focused on actionable defects.

Move this issue to the archive when resolved.

## Issue Entry Template

Copy this section for each new issue.

### Issue ID: ISSUE-XXX

**Summary:**

[One concise sentence describing the issue.]

**Status:**

open

**Priority:**

P2

**Owner or team:**

[Person, role, team, or `Unassigned`.]

**Identified date:**

YYYY-MM-DD

**Target resolution date:**

YYYY-MM-DD or `TBD`

**Resolved date:**

YYYY-MM-DD or `N/A`

**Problem description:**

[Describe what is wrong, missing, confusing, unreliable, or risky. Include enough context for a future session to understand it without exposing secrets.]

**Impact:**

[Explain who or what is affected, how often it happens, and why it matters.]

**Affected areas:**

- `app/routes/`: [If applicable]
- `app/services/`: [If applicable]
- `app/utils/`: [If applicable]
- `app/models.py`: [If applicable]
- `scripts/`: [If applicable]
- `docs/`: [If applicable]
- External provider: [Railway, Strava, Twilio, Supabase, OpenAI, or N/A]

**Proposed solution or next steps:**

1. [First investigation or implementation step]
2. [Second step]
3. [Validation or rollout step]

**Validation plan:**

- [Unit test, compile check, manual check, or provider dashboard check]
- [Expected result]

**Related links or references:**

- [GitHub issue, PR, docs page, runbook section, or provider dashboard reference]

**Notes:**

[Any useful context, decisions, or follow-up reminders.]

## Archived Or Resolved Issues

Move resolved issues here when the active list gets too long.
