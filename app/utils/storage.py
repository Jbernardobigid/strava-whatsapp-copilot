import json

from app.config import PROCESSED_EVENTS_FILE, TOKEN_FILE


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