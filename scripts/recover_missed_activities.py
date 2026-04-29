from pathlib import Path
import sys

# Make sure the project root is on sys.path when running from /scripts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.utils.logger import get_logger
from app.services.coaching_service import build_activity_message
from app.services.strava_service import get_recent_strava_activities, simplify_activity
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.storage import has_processed_event, mark_event_as_processed

logger = get_logger(__name__)


def build_recovery_event(activity_id: int) -> dict:
    return {
        "object_type": "activity",
        "aspect_type": "create",
        "object_id": activity_id,
    }


def recover_missed_activities(limit: int = 10) -> None:
    activities, error = get_recent_strava_activities(per_page=limit)

    if error:
        print(f"Error fetching activities: {error}")
        return

    recovered_count = 0
    skipped_count = 0

    # Oldest first, so WhatsApp messages arrive in chronological order
    for raw_activity in reversed(activities):
        activity_type = raw_activity.get("type")
        activity_id = raw_activity.get("id")

        if activity_type not in ["Ride", "VirtualRide"]:
            skipped_count += 1
            continue

        if not activity_id:
            skipped_count += 1
            continue

        event = build_recovery_event(activity_id)

        if has_processed_event(event):
            print(f"Skipping already processed activity {activity_id}")
            logger.info(
                "Skipped already processed activity during recovery: activity_id=%s",
                activity_id,
            )
            skipped_count += 1
            continue

        activity = simplify_activity(raw_activity)
        body = build_activity_message(activity)

        try:
            send_whatsapp_message(body)
            mark_event_as_processed(event)
            recovered_count += 1
            print(f"Recovered activity {activity_id}: {activity.get('name')}")
            logger.info(
                "Recovered missed activity: activity_id=%s name=%s",
                activity_id,
                activity.get("name"),
            )
        except Exception as exc:
            logger.error(
                "Failed to send recovered activity: activity_id=%s error=%s",
                activity_id,
                exc,
            )

    print()
    print("Recovery finished.")
    print(f"Recovered: {recovered_count}")
    print(f"Skipped: {skipped_count}")


if __name__ == "__main__":
    limit = 10

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Invalid limit. Using default = 10.")

    recover_missed_activities(limit=limit)