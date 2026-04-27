# TrainingBuddy Runbook

_Last updated: 2026-04-24_

This runbook explains how to operate, test, recover, and troubleshoot the TrainingBuddy app.

## 1. Local development

### 1.1 Activate virtual environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 1.2 Run locally

```bash
uvicorn app.main:app --reload
```

Local base URL:

```text
http://127.0.0.1:8000
```

### 1.3 Test health

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### 1.4 Test WhatsApp

```text
http://127.0.0.1:8000/test-whatsapp
```

Expected response:

```json
{
  "status": "sent",
  "message_sid": "SM..."
}
```

Important: this means Twilio accepted the message. Final delivery must be checked in Twilio logs if needed.

## 2. Railway production

### 2.1 Production base URL

```text
https://web-production-d4872.up.railway.app
```

### 2.2 Production health check

```text
https://web-production-d4872.up.railway.app/health
```

Expected response:

```json
{"status":"ok"}
```

### 2.3 Railway logs

Use the Railway dashboard:

```text
Project → Service → Logs
```

Look for:

- app startup logs
- `/health` requests
- Strava webhook verification requests
- Strava webhook POST events
- Twilio Message SID logs
- OpenAI generation logs

## 3. Strava webhook operations

### 3.1 List current webhook subscriptions

PowerShell:

```powershell
curl.exe -G "https://www.strava.com/api/v3/push_subscriptions" `
  -d "client_id=YOUR_CLIENT_ID" `
  -d "client_secret=YOUR_CLIENT_SECRET"
```

Expected current callback URL:

```text
https://web-production-d4872.up.railway.app/webhook/strava
```

### 3.2 Delete a webhook subscription

```powershell
curl.exe -X DELETE "https://www.strava.com/api/v3/push_subscriptions/SUBSCRIPTION_ID?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"
```

### 3.3 Create webhook subscription

```powershell
curl.exe -X POST "https://www.strava.com/api/v3/push_subscriptions" `
  -F "client_id=YOUR_CLIENT_ID" `
  -F "client_secret=YOUR_CLIENT_SECRET" `
  -F "callback_url=https://web-production-d4872.up.railway.app/webhook/strava" `
  -F "verify_token=YOUR_VERIFY_TOKEN"
```

After creating it, Railway logs should show a GET request to `/webhook/strava` with `hub.challenge`.

## 4. Strava OAuth settings

In Strava → My API Application:

Authorization Callback Domain should be:

```text
web-production-d4872.up.railway.app
```

No protocol. No path.

Railway variable should be:

```env
STRAVA_REDIRECT_URI=https://web-production-d4872.up.railway.app/strava/callback
```

## 5. Recovery script

Use this if the app missed a ride or the webhook did not process.

### 5.1 Run recovery for the most recent activity

```bash
python scripts/recover_missed_activities.py 1
```

### 5.2 Run recovery for recent activities

```bash
python scripts/recover_missed_activities.py 10
```

The script should:

- fetch recent Strava activities
- skip already processed activity IDs
- send WhatsApp for missed rides
- mark recovered rides as processed

## 6. Manual resend by activity ID

Use this if an activity was marked processed but the WhatsApp message did not arrive due to Twilio delivery failure.

One-liner:

```bash
python -c "from app.services.strava_service import get_strava_activity_by_id; from app.services.coaching_service import build_activity_message; from app.services.whatsapp_service import send_whatsapp_message; a,_=get_strava_activity_by_id(ACTIVITY_ID); send_whatsapp_message(build_activity_message(a))"
```

Replace `ACTIVITY_ID` with the Strava activity ID.

This does not modify `processed_events.json`.

## 7. Export full Strava activity JSON

Use this to inspect raw Strava data.

```bash
python scripts/export_activity_json.py ACTIVITY_ID
```

Expected output:

```text
activity_ACTIVITY_ID.json
```

These exported files should be ignored by Git.

Recommended `.gitignore` entry:

```gitignore
activity_*.json
```

## 8. Twilio troubleshooting

### 8.1 Message accepted but not delivered

If `/test-whatsapp` returns a SID but no message arrives, check Twilio Console → Messaging Logs.

Common status:

```text
undelivered
```

Common error:

```text
63016 - Failed to send freeform message because you are outside the allowed window.
```

### 8.2 Fix WhatsApp window issue

Send a message from your phone to the Twilio WhatsApp Sandbox number.

Then retry `/test-whatsapp` or resend the activity.

### 8.3 Long-term fix

Use approved WhatsApp templates for outbound messages outside the customer service window.

## 9. Logging

Local logs are stored in:

```text
logs/app.log
```

Logs are ignored by Git.

Useful log events:

- Strava token refresh
- recent activity fetch
- activity fetch by ID
- weekly context build
- AI generation success/failure
- WhatsApp accepted by Twilio
- webhook received
- duplicate webhook ignored
- webhook processed

## 10. Common issues

### 10.1 Wrong Uvicorn command

Correct:

```bash
uvicorn app.main:app --reload
```

Wrong:

```bash
uvicorn app.main.app: --reload
```

### 10.2 Favicon 404

When testing `/health`, browser may also request:

```text
/favicon.ico
```

A 404 for favicon is harmless.

### 10.3 Webhook points to old ngrok URL

List subscriptions and confirm callback URL.

If it still points to ngrok, delete and recreate the subscription with Railway URL.

### 10.4 Duplicate messages

Deduplication is handled through `processed_events.json` using keys like:

```text
activity:create:ACTIVITY_ID
```

If this file resets, duplicate messages may happen again.
