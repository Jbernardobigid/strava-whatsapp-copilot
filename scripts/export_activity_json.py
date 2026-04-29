import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

import requests
from app.services.strava_service import get_valid_strava_access_token


if len(sys.argv) < 2:
    print("Usage: python scripts/export_activity_json.py <activity_id>")
    sys.exit(1)

activity_id = sys.argv[1]
access_token = get_valid_strava_access_token()

if not access_token:
    print("No valid Strava token found.")
    sys.exit(1)

response = requests.get(
    f"https://www.strava.com/api/v3/activities/{activity_id}",
    headers={"Authorization": f"Bearer {access_token}"},
    timeout=30,
)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
    sys.exit(1)

activity = response.json()

output_file = PROJECT_ROOT / f"activity_{activity_id}.json"
output_file.write_text(
    json.dumps(activity, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Saved full activity JSON to {output_file}")