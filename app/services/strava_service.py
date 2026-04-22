import time
from datetime import datetime, timedelta, timezone

import requests

from app.config import (
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REDIRECT_URI,
)
from app.utils.storage import load_strava_tokens, save_strava_tokens


def refresh_strava_token_if_needed() -> dict | None:
    token_data = load_strava_tokens()
    if not token_data:
        return None

    expires_at = token_data.get("expires_at")
    refresh_token = token_data.get("refresh_token")

    if not expires_at or not refresh_token:
        return token_data

    now = int(time.time())

    if now < expires_at - 300:
        return token_data

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise Exception(f"Failed to refresh Strava token: {response.text}")

    new_token_data = response.json()
    save_strava_tokens(new_token_data)
    return new_token_data


def get_valid_strava_access_token() -> str | None:
    token_data = refresh_strava_token_if_needed()
    if not token_data:
        return None
    return token_data.get("access_token")


def build_strava_auth_url() -> dict:
    if not STRAVA_CLIENT_ID or not STRAVA_REDIRECT_URI:
        return {"error": "Missing STRAVA_CLIENT_ID or STRAVA_REDIRECT_URI in .env"}

    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=read,activity:read"
    )

    return {"auth_url": url}


def exchange_code_for_token(code: str) -> dict:
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    data = response.json()
    save_strava_tokens(data)
    return data


def simplify_activity(activity: dict) -> dict:
    return {
        "name": activity.get("name"),
        "distance_km": round(activity.get("distance", 0) / 1000, 2),
        "moving_time_min": round(activity.get("moving_time", 0) / 60),
        "elevation_gain_m": round(activity.get("total_elevation_gain", 0), 1),
        "type": activity.get("type"),
        "start_date": activity.get("start_date"),
    }


def get_latest_strava_activity():
    access_token = get_valid_strava_access_token()

    if not access_token:
        return None, "No Strava token found. First visit /connect-strava and authorize."

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"per_page": 1, "page": 1},
        timeout=30,
    )

    if response.status_code != 200:
        return None, f"Failed to fetch activities: {response.status_code} - {response.text}"

    activities = response.json()

    if not activities:
        return None, "No activities found in Strava."

    return simplify_activity(activities[0]), None


def get_strava_activity_by_id(activity_id: int):
    access_token = get_valid_strava_access_token()

    if not access_token:
        return None, "No Strava token found. First visit /connect-strava and authorize."

    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        return None, f"Failed to fetch activity {activity_id}: {response.status_code} - {response.text}"

    activity = response.json()
    return simplify_activity(activity), None


def get_recent_strava_activities(per_page: int = 30):
    access_token = get_valid_strava_access_token()

    if not access_token:
        return None, "No Strava token found. First visit /connect-strava and authorize."

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"per_page": per_page, "page": 1},
        timeout=30,
    )

    if response.status_code != 200:
        return None, f"Failed to fetch recent activities: {response.status_code} - {response.text}"

    return response.json(), None


def parse_strava_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def build_weekly_context() -> tuple[dict | None, str | None]:
    activities, error = get_recent_strava_activities(per_page=30)

    if error:
        return None, error

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

    current_week = []
    previous_week = []

    for activity in activities:
        start_date = activity.get("start_date")
        activity_type = activity.get("type")

        if not start_date or activity_type not in ["Ride", "VirtualRide"]:
            continue

        dt = parse_strava_datetime(start_date)

        if dt >= seven_days_ago:
            current_week.append(activity)
        elif fourteen_days_ago <= dt < seven_days_ago:
            previous_week.append(activity)

    current_count = len(current_week)
    current_distance = round(sum(a.get("distance", 0) for a in current_week) / 1000, 1)
    previous_distance = round(sum(a.get("distance", 0) for a in previous_week) / 1000, 1)

    if previous_distance == 0 and current_distance > 0:
        trend = "Em relação aos 7 dias anteriores, seu volume está em alta."
    elif current_distance > previous_distance * 1.1:
        trend = "Em relação aos 7 dias anteriores, seu volume está em alta."
    elif current_distance < previous_distance * 0.9:
        trend = "Em relação aos 7 dias anteriores, seu volume está em baixa."
    else:
        trend = "Em relação aos 7 dias anteriores, seu volume está estável."

    extra = ""
    if current_distance >= 500:
        extra = "Volume bem alto na última semana — atenção à recuperação."
    elif current_distance >= 300:
        extra = "Boa carga recente, vale cuidar da recuperação."

    from app.utils.formatters import format_number_pt_br

    summary = (
        f"{current_count} pedais nos últimos 7 dias • {format_number_pt_br(current_distance)} km\n"
        f"{trend}"
    )

    if extra:
        summary += f"\n{extra}"

    return {
        "summary": summary,
        "current_count": current_count,
        "current_distance": current_distance,
        "previous_distance": previous_distance,
        "trend": trend,
        "extra": extra,
    }, None