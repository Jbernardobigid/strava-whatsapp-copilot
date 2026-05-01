from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from app.utils.logger import get_logger
from app.config import STRAVA_VERIFY_TOKEN
from app.services.coaching_service import build_activity_message
from app.services.strava_service import build_weekly_context, get_strava_activity_by_id
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.storage import (
    has_processed_event,
    mark_event_as_processed,
    resolve_app_user_for_webhook_event,
)

logger = get_logger(__name__)

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

    logger.info(
        "Strava webhook event received: object_type=%s aspect_type=%s object_id=%s event_time=%s owner_id=%s",
        event.get("object_type"),
        event.get("aspect_type"),
        event.get("object_id"),
        event.get("event_time"),
        event.get("owner_id"),
    )

    if has_processed_event(event):
        logger.info(
            "Duplicate webhook event ignored: object_id=%s",
            event.get("object_id"),
        )
        return {"received": True, "duplicate": True}

    object_type = event.get("object_type")
    aspect_type = event.get("aspect_type")

    if object_type == "activity" and aspect_type == "create":
        activity_id = event.get("object_id")
        app_user = resolve_app_user_for_webhook_event(event)

        if event.get("owner_id") and not app_user:
            logger.warning(
                "Strava webhook skipped because owner_id is not mapped: object_id=%s owner_id=%s",
                activity_id,
                event.get("owner_id"),
            )
            return {"received": True, "skipped": "unknown_owner"}

        user_id = app_user.get("id") if app_user else None
        athlete_id = app_user.get("strava_athlete_id") if app_user else event.get("owner_id")
        whatsapp_number = app_user.get("whatsapp_number") if app_user else None

        activity, error = get_strava_activity_by_id(
            activity_id,
            user_id=user_id,
            athlete_id=athlete_id,
        )

        if not error and activity:
            body = build_activity_message(
                activity,
                user_id=user_id,
                athlete_id=athlete_id,
            )
            send_whatsapp_message(
                body,
                to_number=whatsapp_number,
                user_id=user_id,
                strava_activity_id=activity_id,
            )
            mark_event_as_processed(event, user_id=user_id)
            logger.info(
                "Webhook processed and WhatsApp message sent: object_id=%s user_id=%s",
                activity_id,
                user_id,
            )
        else:
            logger.error(
                "Failed to fetch activity from webhook: object_id=%s error=%s",
                activity_id,
                error,
            )

    return {"received": True}