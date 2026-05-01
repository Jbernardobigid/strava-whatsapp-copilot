# Documentation Index

This folder contains long-standing documentation for TrainingBuddy / Strava WhatsApp Copilot. These docs explain how the system works, why decisions were made, and how to operate the app safely.

## Current Docs

- [Context Handoff](CONTEXT_HANDOFF.md) — Start here when opening a new ChatGPT/Codex session.
- [Project State](PROJECT_STATE.md) — Current working status, known limitations, and recommended next milestones.
- [Architecture](ARCHITECTURE.md) — Stack, folder structure, runtime flow, persistence model, and key modules.
- [Runbook](RUNBOOK.md) — Local development, Railway operations, Strava/Twilio checks, recovery, and troubleshooting.
- [Technical Decisions](DECISIONS.md) — Important product and engineering decisions already made.
- [Roadmap](ROADMAP.md) — Longer-term product and technical direction.
- [Issue Tracker](ISSUE_TRACKER.md) — Active issues, priorities, owners, validation plans, and resolved issue archive.
- [Session Log](SESSION_LOG.md) — Chronological project progress notes.

## Planning Templates

- [Feature Planning Template](../plans/FEATURE_PLANNING_TEMPLATE.md) — Use this before implementing larger product changes.

## Guidelines for Writing Docs

1. One topic per file. Name files descriptively.
2. Start with what it does, then how, then why.
3. Keep docs current. If you change a system, update the corresponding doc in the same PR.
4. Do not document what is obvious from the code.
5. Focus on decisions, constraints, external dependencies, operational steps, and anything that would take 30+ minutes to infer from source.
6. Include examples for non-obvious interfaces, payloads, env vars, commands, or workflows.
7. Avoid generated boilerplate. Every sentence should earn its place.

## What Does Not Belong Here

- Task lists or TODOs → `plans/` or `docs/ISSUE_TRACKER.md`
- Temporary notes or scratch work → `temp/` if needed and gitignored
- Code comments explaining implementation details → keep those in the code
- Git history or changelog → use git history
- Secrets, tokens, raw phone numbers, activity exports, logs, or local runtime files → never commit
