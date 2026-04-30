# AGENTS.md

## Project overview

This project is TrainingBuddy, a Strava → WhatsApp cycling copilot.

The app receives Strava webhook events, fetches the related activity, builds a Brazilian Portuguese coaching message, and sends it through Twilio WhatsApp.

The app is deployed on Railway.

## Repository structure

- `app/main.py`: FastAPI app entrypoint
- `app/routes/`: HTTP routes
- `app/services/`: Strava, WhatsApp, coaching, and AI logic
- `app/utils/`: logging, formatting, and file storage helpers
- `scripts/`: operational scripts such as recovery/backfill
- `docs/`: project documentation and runbooks

## Important behavior

- WhatsApp messages must be written in Brazilian Portuguese.
- Do not remove fallback behavior if OpenAI fails.
- Do not break Strava webhook verification.
- Do not break duplicate protection.
- Do not expose or log secrets.
- Do not commit `.env`, `strava_tokens.json`, `processed_events.json`, activity JSON exports, SSH keys, or API keys.
- Treat Railway filesystem persistence as temporary unless a volume or database is explicitly added.

## Security rules

Never log or expose:

- Strava access tokens
- Strava refresh tokens
- Twilio auth token
- OpenAI API key
- WhatsApp phone numbers unless already intentionally logged in masked form

## Development commands

Before proposing changes, prefer running:

```bash
python -m compileall app scripts