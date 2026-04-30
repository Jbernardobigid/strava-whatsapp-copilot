import time
from datetime import datetime, timedelta, timezone

import requests

from app.config import (
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_REDIRECT_URI,
)
from app.utils.formatters import format_number_pt_br
from app.utils.logger import get_logger
from app.utils.storage import load_strava_tokens, save_strava_tokens

logger = get_logger(__name__)


def refresh_strava_token_if_needed() -> dict | None:
    token_data = load_strava_tokens()
    if not token_data:
        return None

    expires_at = token_data.get("expires_at")
    refresh_token = token_data.get("refresh_token")

    if not expires_at or not refresh_token:
        return token_data

    now = int(time.time())

    # Refresh if expired or close to expiring
    if now < expires_at - 300:
        return token_data

    logger.info("Refreshing Strava access token")

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
        logger.error(
            "Failed to refresh Strava token: status_code=%s response=%s",
            response.status_code,
            response.text,
        )
        raise Exception(f"Failed to refresh Strava token: {response.text}")

    new_token_data = response.json()
    save_strava_tokens(new_token_data)

    logger.info("Strava access token refreshed successfully")

    return new_token_data


def get_valid_strava_access_token() -> str | None:
    token_data = refresh_strava_token_if_needed()
    if not token_data:
        return None

    return token_data.get("access_token")


def build_strava_auth_url() -> str | dict:
    if not STRAVA_CLIENT_ID or not STRAVA_REDIRECT_URI:
        logger.error("Missing STRAVA_CLIENT_ID or STRAVA_REDIRECT_URI in .env")
        return {"error": "Missing STRAVA_CLIENT_ID or STRAVA_REDIRECT_URI in .env"}

    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        "&approval_prompt=force"
        "&scope=read,activity:read"
    )

    logger.info("Generated Strava authorization URL")

    return url


def exchange_code_for_token(code: str) -> dict:
    logger.info("Exchanging Strava authorization code for token")

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

    if response.status_code != 200:
        logger.error(
            "Failed to exchange Strava authorization code: status_code=%s response=%s",
            response.status_code,
            response.text,
        )
        return {"error": response.text}

    data = response.json()
    save_strava_tokens(data)

    athlete = data.get("athlete", {})
    logger.info(
        "Strava token saved successfully: athlete_id=%s",
        athlete.get("id"),
    )

    return data


def simplify_activity(activity: dict) -> dict:
    return {
        "id": activity.get("id"),
        "name": activity.get("name"),
        "distance_km": round(activity.get("distance", 0) / 1000, 2),
        "moving_time_min": round(activity.get("moving_time", 0) / 60),
        "elevation_gain_m": round(activity.get("total_elevation_gain", 0), 1),
        "type": activity.get("type"),
        "start_date": activity.get("start_date"),

        # Intensity metrics
        "average_speed": activity.get("average_speed"),
        "max_speed": activity.get("max_speed"),
        "average_watts": activity.get("average_watts"),
        "weighted_average_watts": activity.get("weighted_average_watts"),
        "max_watts": activity.get("max_watts"),
        "kilojoules": activity.get("kilojoules"),

        # Heart rate metrics
        "has_heartrate": activity.get("has_heartrate"),
        "average_heartrate": activity.get("average_heartrate"),
        "max_heartrate": activity.get("max_heartrate"),

        # Strava effort indicators
        "suffer_score": activity.get("suffer_score"),
        "achievement_count": activity.get("achievement_count"),
        "pr_count": activity.get("pr_count"),

        # Structured blocks
        "laps": activity.get("laps", []),
        "splits_metric": activity.get("splits_metric", []),
        "segment_efforts": activity.get("segment_efforts", []),
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
        logger.error(
            "Failed to fetch latest Strava activity: status_code=%s response=%s",
            response.status_code,
            response.text,
        )
        return None, f"Failed to fetch activities: {response.status_code} - {response.text}"

    activities = response.json()

    if not activities:
        logger.info("No Strava activities found when fetching latest activity")
        return None, "No activities found in Strava."

    latest_activity = simplify_activity(activities[0])

    logger.info(
        "Fetched latest Strava activity: activity_id=%s name=%s",
        latest_activity.get("id"),
        latest_activity.get("name"),
    )

    return latest_activity, None


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
        logger.error(
            "Failed to fetch Strava activity by id: activity_id=%s status_code=%s response=%s",
            activity_id,
            response.status_code,
            response.text,
        )
        return None, f"Failed to fetch activity {activity_id}: {response.status_code} - {response.text}"

    activity = response.json()
    simplified_activity = simplify_activity(activity)

    logger.info(
        "Fetched Strava activity by id: activity_id=%s name=%s",
        activity_id,
        simplified_activity.get("name"),
    )

    return simplified_activity, None


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
        logger.error(
            "Failed to fetch recent Strava activities: status_code=%s response=%s",
            response.status_code,
            response.text,
        )
        return None, f"Failed to fetch recent activities: {response.status_code} - {response.text}"

    activities = response.json()

    logger.info(
        "Fetched recent Strava activities: per_page=%s count=%s",
        per_page,
        len(activities),
    )

    return activities, None


def parse_strava_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def build_weekly_context() -> tuple[dict | None, str | None]:
    activities, error = get_recent_strava_activities(per_page=30)

    if error:
        return None, error

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

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

    summary = (
        f"{current_count} pedais nos últimos 7 dias • {format_number_pt_br(current_distance)} km\n"
        f"{trend}"
    )

    if extra:
        summary += f"\n{extra}"

    logger.info(
        "Built weekly context: current_count=%s current_distance=%s previous_distance=%s",
        current_count,
        current_distance,
        previous_distance,
    )

    return {
        "summary": summary,
        "current_count": current_count,
        "current_distance": current_distance,
        "previous_distance": previous_distance,
        "trend": trend,
        "extra": extra,
    }, None