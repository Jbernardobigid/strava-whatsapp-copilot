from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.services.coaching_service import build_activity_message
from app.services.strava_service import (
    build_strava_auth_url,
    exchange_code_for_token,
    get_latest_strava_activity,
    get_recent_strava_activities,
    simplify_activity,
)
from app.services.whatsapp_service import send_whatsapp_message
from app.utils.storage import get_strava_token_status

router = APIRouter()


@router.get("/test-whatsapp")
def test_whatsapp():
    message_sid = send_whatsapp_message(
        "Mensagem de teste do Strava WhatsApp Copilot 🚴"
    )
    return {
        "status": "sent",
        "message_sid": message_sid,
    }


@router.get("/connect-strava")
def connect_strava():
    auth_url = build_strava_auth_url()

    if isinstance(auth_url, dict):
        return auth_url

    return RedirectResponse(url=auth_url)


@router.get("/debug/strava-token-status")
def debug_strava_token_status():
    return get_strava_token_status()


@router.get("/strava/callback")
def strava_callback(code: str):
    data = exchange_code_for_token(code)
    return {
        "message": "Strava connected successfully",
        "athlete": data.get("athlete"),
        "token_saved_to_file": True,
    }


@router.get("/strava/activities")
def get_strava_activities():
    activities, error = get_recent_strava_activities(per_page=5)

    if error:
        return {"error": error}

    simplified = [simplify_activity(activity) for activity in activities]

    return {
        "count": len(simplified),
        "activities": simplified,
    }


@router.get("/send-latest-activity-whatsapp")
def send_latest_activity_whatsapp():
    activity, error = get_latest_strava_activity()

    if error:
        return {"error": error}

    body = build_activity_message(activity)
    message_sid = send_whatsapp_message(body)

    return {
        "status": "sent",
        "message_sid": message_sid,
        "activity": activity,
    }