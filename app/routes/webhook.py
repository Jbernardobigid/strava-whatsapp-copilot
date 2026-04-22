from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.config import STRAVA_VERIFY_TOKEN
from app.services.coaching_service import build_activity_message
from app.services.strava_service import build_weekly_context, get_strava_activity_by_id
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.storage import has_processed_event, mark_event_as_processed

router = APIRouter()


@router.get("/debug/weekly-context")
def debug_weekly_context():
    weekly_context, weekly_error = build_weekly_context()
    return {
        "weekly_context": weekly_context,
        "weekly_error": weekly_error,
    }


@router.get("/webhook/strava")
def verify_strava_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    if hub_mode != "subscribe" or hub_verify_token != STRAVA_VERIFY_TOKEN:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid webhook verification request"},
        )

    return {"hub.challenge": hub_challenge}


@router.post("/webhook/strava")
async def receive_strava_webhook(request: Request):
    event = await request.json()

    print(
        f"Strava webhook event received: object_type={event.get('object_type')} "
        f"aspect_type={event.get('aspect_type')} object_id={event.get('object_id')} "
        f"event_time={event.get('event_time')}"
    )

    if has_processed_event(event):
        print("Duplicate webhook event ignored.")
        return {"received": True, "duplicate": True}

    object_type = event.get("object_type")
    aspect_type = event.get("aspect_type")

    if object_type == "activity" and aspect_type == "create":
        activity_id = event.get("object_id")
        activity, error = get_strava_activity_by_id(activity_id)

        if not error and activity:
            body = build_activity_message(activity)
            send_whatsapp_message(body)
            mark_event_as_processed(event)
            print("Webhook processed and message sent.")
        else:
            print(f"Failed to fetch activity: {error}")

    return {"received": True}