import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.services.strava_service import get_strava_activity_by_id
from app.services.coaching_service import build_activity_message
from app.services.whatsapp_service import send_whatsapp_message

if len(sys.argv) < 2:
    print("Usage: python resend_activity.py <activity_id>")
    sys.exit(1)

activity_id = int(sys.argv[1])

activity, error = get_strava_activity_by_id(activity_id)

if error:
    print(error)
    sys.exit(1)

body = build_activity_message(activity)
send_whatsapp_message(body)

print(f"Resent activity {activity_id}")