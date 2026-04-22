import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytz
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from twilio.rest import Client

load_dotenv()

app = FastAPI(title="Strava WhatsApp Copilot")

TOKEN_FILE = Path("strava_tokens.json")
PROCESSED_EVENTS_FILE = Path("processed_events.json")


def save_strava_tokens(token_data: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def load_strava_tokens() -> dict | None:
    if not TOKEN_FILE.exists():
        return None

    content = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not content:
        return None

    return json.loads(content)


def load_processed_events() -> set[str]:
    if not PROCESSED_EVENTS_FILE.exists():
        return set()

    content = PROCESSED_EVENTS_FILE.read_text(encoding="utf-8").strip()
    if not content:
        return set()

    return set(json.loads(content))


def save_processed_events(event_ids: set[str]) -> None:
    PROCESSED_EVENTS_FILE.write_text(
        json.dumps(sorted(event_ids), indent=2),
        encoding="utf-8",
    )


def build_event_key(event: dict) -> str:
    object_type = event.get("object_type", "")
    aspect_type = event.get("aspect_type", "")
    object_id = event.get("object_id", "")
    return f"{object_type}:{aspect_type}:{object_id}"


def has_processed_event(event: dict) -> bool:
    event_key = build_event_key(event)
    processed = load_processed_events()
    return event_key in processed


def mark_event_as_processed(event: dict) -> None:
    event_key = build_event_key(event)
    processed = load_processed_events()
    processed.add(event_key)
    save_processed_events(processed)


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

    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
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


def send_whatsapp_message(body: str) -> str:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    to_number = os.getenv("YOUR_WHATSAPP_NUMBER")

    missing = []
    if not account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not auth_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not from_number:
        missing.append("TWILIO_WHATSAPP_NUMBER")
    if not to_number:
        missing.append("YOUR_WHATSAPP_NUMBER")

    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=body,
        from_=from_number,
        to=to_number,
    )

    return message.sid


def translate_activity_type(activity_type: str) -> str:
    type_map = {
        "Ride": "Pedalada",
        "VirtualRide": "Pedalada virtual",
    }
    return type_map.get(activity_type, activity_type)


def classify_ride(activity: dict) -> str:
    distance = activity["distance_km"]
    moving_time = activity["moving_time_min"]
    elevation = activity["elevation_gain_m"]

    if distance >= 100:
        return "longo"
    if elevation >= 1000:
        return "de escalada"
    if moving_time < 45:
        return "curto"
    if distance >= 50 or moving_time >= 120:
        return "moderado"
    return "leve"


def interpret_ride(activity: dict, ride_classification: str) -> str:
    distance = activity["distance_km"]
    elevation = activity["elevation_gain_m"]
    moving_time = activity["moving_time_min"]

    if ride_classification == "longo":
        return "Esse pedal parece ter sido um treino longo de endurance, com boa carga geral."
    if ride_classification == "de escalada":
        return "Esse pedal teve bastante elevação e provavelmente exigiu mais das pernas do que um giro plano."
    if ride_classification == "curto":
        return "Esse pedal foi mais curto e pode ter funcionado como giro leve, deslocamento ou treino rápido."
    if ride_classification == "moderado":
        return "Esse pedal parece ter sido um endurance moderado, com estímulo consistente."
    if distance < 30 and moving_time < 60 and elevation < 300:
        return "Esse pedal parece leve e controlado, bom para manter consistência."
    return "Esse treino teve um bom estímulo geral."


def suggest_next_day(
    activity: dict,
    ride_classification: str,
    weekly_distance: float = 0,
) -> str:
    moving_time = activity["moving_time_min"]

    if weekly_distance >= 500:
        return "Amanhã vale priorizar recuperação completa."

    if ride_classification == "longo":
        return "Amanhã vale priorizar recuperação: descanso ou giro bem leve."

    if ride_classification == "de escalada":
        return "Amanhã pode ser um bom dia para rodar leve e soltar as pernas."

    if moving_time >= 150:
        return "Como o tempo de esforço foi alto, o ideal amanhã é recuperação."

    if ride_classification == "curto":
        return "Se estiver bem, amanhã pode encaixar um treino mais estruturado."

    return "Se estiver se sentindo bem, faça um giro leve. Se estiver cansado, descanse."


def format_datetime_pt_br(iso_string: str) -> str:
    dt_utc = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    tz = pytz.timezone("America/Sao_Paulo")
    dt_local = dt_utc.astimezone(tz)
    return dt_local.strftime("%d/%m às %H:%M")


def format_number_pt_br(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_duration_pt_br(total_minutes: float) -> str:
    total_minutes_int = round(total_minutes)
    hours = total_minutes_int // 60
    minutes = total_minutes_int % 60

    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}min"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}min"


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


def build_ride_title(activity: dict, ride_classification: str) -> str:
    name = activity.get("name", "").lower()

    if "morning" in name or "manhã" in name:
        return "Pedalada matinal 🚴"
    if "evening" in name or "noite" in name:
        return "Pedalada noturna 🌙"
    if "commute" in name:
        return "Pedal do dia a dia 🚲"

    if ride_classification == "longo":
        return "Treino longo 🚴"
    if ride_classification == "de escalada":
        return "Treino de subida ⛰️"
    if ride_classification == "moderado":
        return "Bom pedal 🚴"
    if ride_classification == "curto":
        return "Giro rápido ⚡"

    return "Bom pedal 🚴"


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

    return {
        "summary": summary,
        "current_count": current_count,
        "current_distance": current_distance,
        "previous_distance": previous_distance,
        "trend": trend,
        "extra": extra,
    }, None


def build_activity_message(activity: dict) -> str:
    tipo = translate_activity_type(activity["type"])
    ride_classification = classify_ride(activity)

    weekly_context, weekly_error = build_weekly_context()
    weekly_distance = 0.0
    weekly_summary = ""

    if weekly_context and not weekly_error:
        weekly_distance = weekly_context.get("current_distance", 0.0)
        weekly_summary = weekly_context.get("summary", "")

    interpretation = interpret_ride(activity, ride_classification)
    next_day = suggest_next_day(activity, ride_classification, weekly_distance)

    tempo_formatado = format_duration_pt_br(activity["moving_time_min"])
    distancia = format_number_pt_br(activity["distance_km"])
    elevacao = int(activity["elevation_gain_m"])

    titulo = build_ride_title(activity, ride_classification)

    data_formatada = ""
    if activity.get("start_date"):
        data_formatada = format_datetime_pt_br(activity["start_date"])

    contexto_bloco = ""
    if weekly_summary:
        contexto_bloco = (
            "Seu contexto recente:\n"
            f"{weekly_summary}\n\n"
        )

    return (
        f"{titulo}\n\n"
        f"{activity['name']}\n"
        f"{tipo} • {distancia} km • {tempo_formatado} • {elevacao} m\n"
        f"{data_formatada}\n\n"
        "Leitura do treino:\n"
        f"{interpretation}\n\n"
        f"{contexto_bloco}"
        "Sugestão para amanhã:\n"
        f"{next_day}"
    )


@app.get("/")
def home():
    return {"message": "Strava WhatsApp Copilot is running"}


@app.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})


@app.get("/test-whatsapp")
def test_whatsapp():
    message_sid = send_whatsapp_message(
        "Mensagem de teste do Strava WhatsApp Copilot 🚴"
    )
    return {
        "status": "sent",
        "message_sid": message_sid,
    }


@app.get("/connect-strava")
def connect_strava():
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI")

    if not client_id or not redirect_uri:
        return {"error": "Missing STRAVA_CLIENT_ID or STRAVA_REDIRECT_URI in .env"}

    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        "&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&approval_prompt=force"
        "&scope=read,activity:read"
    )

    return {"auth_url": url}


@app.get("/strava/callback")
def strava_callback(code: str):
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    data = response.json()
    save_strava_tokens(data)

    return {
        "message": "Strava connected successfully",
        "athlete": data.get("athlete"),
        "token_saved_to_file": True,
    }


@app.get("/strava/activities")
def get_strava_activities():
    access_token = get_valid_strava_access_token()

    if not access_token:
        return {
            "error": "No Strava token found. First visit /connect-strava and authorize."
        }

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"per_page": 5, "page": 1},
        timeout=30,
    )

    if response.status_code != 200:
        return {
            "error": "Failed to fetch activities",
            "status_code": response.status_code,
            "details": response.text,
        }

    activities = response.json()
    simplified = [simplify_activity(activity) for activity in activities]

    return {
        "count": len(simplified),
        "activities": simplified,
    }


@app.get("/send-latest-activity-whatsapp")
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


@app.get("/debug/weekly-context")
def debug_weekly_context():
    weekly_context, weekly_error = build_weekly_context()
    return {
        "weekly_context": weekly_context,
        "weekly_error": weekly_error,
    }


@app.get("/webhook/strava")
def verify_strava_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
):
    expected_token = os.getenv("STRAVA_VERIFY_TOKEN")

    if hub_mode != "subscribe" or hub_verify_token != expected_token:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid webhook verification request"},
        )

    return {"hub.challenge": hub_challenge}


@app.post("/webhook/strava")
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