from datetime import datetime

import pytz


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


def normalize_activity_name(name: str) -> str:
    name_lower = name.lower()

    if "morning ride" in name_lower:
        return "Pedalada matinal"
    if "afternoon ride" in name_lower:
        return "Pedalada da tarde"
    if "evening ride" in name_lower:
        return "Pedalada noturna"

    return name