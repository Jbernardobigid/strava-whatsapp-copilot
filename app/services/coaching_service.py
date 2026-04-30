from app.services.ai_service import generate_ai_training_interpretation
from app.services.strava_service import build_weekly_context
from app.utils.formatters import (
    format_datetime_pt_br,
    format_duration_pt_br,
    format_number_pt_br,
    normalize_activity_name,
)


def classify_ride(activity: dict) -> str:
    distance = activity["distance_km"]
    moving_time = activity["moving_time_min"]
    elevation = activity["elevation_gain_m"]

    average_watts = activity.get("average_watts") or 0
    weighted_watts = activity.get("weighted_average_watts") or 0
    max_watts = activity.get("max_watts") or 0

    average_hr = activity.get("average_heartrate") or 0
    max_hr = activity.get("max_heartrate") or 0

    suffer_score = activity.get("suffer_score") or 0
    pr_count = activity.get("pr_count") or 0
    achievement_count = activity.get("achievement_count") or 0

    laps = activity.get("laps") or []

    hard_laps = 0
    for lap in laps:
        lap_avg_watts = lap.get("average_watts") or 0
        lap_avg_hr = lap.get("average_heartrate") or 0
        lap_max_hr = lap.get("max_heartrate") or 0

        if lap_avg_watts >= 180 or lap_avg_hr >= 160 or lap_max_hr >= 175:
            hard_laps += 1

    if (
        max_hr >= 175
        or max_watts >= 700
        or weighted_watts >= 180
        or suffer_score >= 50
        or pr_count >= 3
        or hard_laps >= 2
    ):
        return "intervalado"

    if distance >= 100:
        return "longo"

    if elevation >= 1000:
        return "de escalada"

    if moving_time < 45:
        return "curto"

    if distance >= 50 or moving_time >= 120:
        return "moderado"

    if (
        average_hr > 0 and average_hr < 120
        and weighted_watts > 0 and weighted_watts < 130
        and distance < 40
    ):
        return "leve"

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

    if ride_classification == "intervalado":
        return "Amanhã vale priorizar recuperação ou um giro bem leve."
    
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


def translate_activity_type(activity_type: str) -> str:
    type_map = {
        "Ride": "Pedalada",
        "VirtualRide": "Pedalada virtual",
    }
    return type_map.get(activity_type, activity_type)


def build_ride_title(activity: dict, ride_classification: str) -> str:
    name = activity.get("name", "").lower()

    if ride_classification == "intervalado":
        return "Treino intervalado 🔥"
    if ride_classification == "longo":
        return "Treino longo 🚴"
    if ride_classification == "de escalada":
        return "Treino de subida ⛰️"
    if ride_classification == "moderado":
        return "Bom pedal 🚴"
    if ride_classification == "curto":
        return "Giro rápido ⚡"

    if "morning" in name or "manhã" in name:
        return "Pedalada matinal 🚴"
    if "evening" in name or "noite" in name:
        return "Pedalada noturna 🌙"
    if "commute" in name:
        return "Pedal do dia a dia 🚲"

    return "Bom pedal 🚴"


def build_activity_message(activity: dict) -> str:
    tipo = translate_activity_type(activity["type"])
    ride_classification = classify_ride(activity)

    weekly_context, weekly_error = build_weekly_context()
    weekly_distance = 0.0
    weekly_summary = ""

    if weekly_context and not weekly_error:
        weekly_distance = weekly_context.get("current_distance", 0.0)
        weekly_summary = weekly_context.get("summary", "")

    fallback_interpretation = interpret_ride(activity, ride_classification)
    interpretation = generate_ai_training_interpretation(
        activity=activity,
        ride_classification=ride_classification,
        weekly_context=weekly_context,
        fallback_text=fallback_interpretation,
    )
    next_day = suggest_next_day(activity, ride_classification, weekly_distance)

    tempo_formatado = format_duration_pt_br(activity["moving_time_min"])
    distancia = format_number_pt_br(activity["distance_km"])
    elevacao = int(activity["elevation_gain_m"])

    titulo = build_ride_title(activity, ride_classification)
    nome = normalize_activity_name(activity["name"])

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
        f"{nome}\n"
        f"{tipo} • {distancia} km • {tempo_formatado} • {elevacao} m\n"
        f"{data_formatada}\n\n"
        "Leitura do treino:\n"
        f"{interpretation}\n\n"
        f"{contexto_bloco}"
        "Sugestão para amanhã:\n"
        f"{next_day}"
    )