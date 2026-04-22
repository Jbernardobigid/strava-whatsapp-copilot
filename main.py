import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from twilio.rest import Client

load_dotenv()

app = FastAPI(title="Strava WhatsApp Copilot")

TOKEN_FILE = Path("strava_tokens.json")


def save_strava_tokens(token_data: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def load_strava_tokens() -> dict | None:
    if not TOKEN_FILE.exists():
        return None

    content = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not content:
        return None

    return json.loads(content)


def refresh_strava_token_if_needed() -> dict | None:
    token_data = load_strava_tokens()
    if not token_data:
        return None

    expires_at = token_data.get("expires_at")
    refresh_token = token_data.get("refresh_token")

    if not expires_at or not refresh_token:
        return token_data

    import time
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


def suggest_next_day(activity: dict, ride_classification: str) -> str:
    elevation = activity["elevation_gain_m"]
    moving_time = activity["moving_time_min"]

    if ride_classification == "longo":
        return "Amanhã vale priorizar recuperação: descanso ou giro bem leve."
    if ride_classification == "de escalada":
        return "Amanhã pode ser um bom dia para rodar leve e soltar as pernas."
    if moving_time >= 150:
        return "Como o tempo de esforço foi alto, o ideal amanhã é recuperação."
    if ride_classification == "curto":
        return "Se estiver bem, amanhã pode encaixar um treino mais estruturado."
    return "Se estiver se sentindo bem, faça um giro leve. Se estiver cansado, descanse."


def format_duration_pt_br(total_minutes: float) -> str:
    total_minutes_int = round(total_minutes)
    hours = total_minutes_int // 60
    minutes = total_minutes_int % 60

    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}min"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}min"


def build_activity_message(activity: dict) -> str:
    tipo = translate_activity_type(activity["type"])
    ride_classification = classify_ride(activity)
    interpretation = interpret_ride(activity, ride_classification)
    next_day = suggest_next_day(activity, ride_classification)
    tempo_formatado = format_duration_pt_br(activity["moving_time_min"])

    return (
        "Bom pedal 🚴\n\n"
        f"{activity['name']}\n"
        f"{tipo} • {activity['distance_km']} km • {tempo_formatado} • {activity['elevation_gain_m']} m\n\n"
        "Leitura do treino:\n"
        f"{interpretation}\n\n"
        "Sugestão para amanhã:\n"
        f"{next_day}"
    )


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

    activity = activities[0]

    simplified = {
        "name": activity.get("name"),
        "distance_km": round(activity.get("distance", 0) / 1000, 2),
        "moving_time_min": round(activity.get("moving_time", 0) / 60),
        "elevation_gain_m": round(activity.get("total_elevation_gain", 0), 1),
        "type": activity.get("type"),
        "start_date": activity.get("start_date"),
    }

    return simplified, None


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
        return {
            "error": "Missing STRAVA_CLIENT_ID or STRAVA_REDIRECT_URI in .env"
        }

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

    token_url = "https://www.strava.com/oauth/token"

    response = requests.post(
        token_url,
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

    simplified = []
    for activity in activities:
        simplified.append(
            {
                "name": activity.get("name"),
                "distance_km": round(activity.get("distance", 0) / 1000, 2),
                "moving_time_min": round(activity.get("moving_time", 0) / 60),
                "elevation_gain_m": activity.get("total_elevation_gain", 0),
                "type": activity.get("type"),
                "start_date": activity.get("start_date"),
            }
        )

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