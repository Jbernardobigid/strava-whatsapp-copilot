import json

from sqlalchemy.exc import IntegrityError

from app import database
from app.config import TOKEN_FILE
from app.models import ProcessedEvent


def save_strava_tokens(token_data: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")


def load_strava_tokens() -> dict | None:
    if not TOKEN_FILE.exists():
        return None

    content = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not content:
        return None

    return json.loads(content)


def build_event_key(event: dict) -> str:
    object_type = event.get("object_type", "")
    aspect_type = event.get("aspect_type", "")
    object_id = event.get("object_id", "")
    return f"{object_type}:{aspect_type}:{object_id}"


def _event_identity(event: dict) -> dict:
    return {
        "object_type": str(event.get("object_type", "")),
        "aspect_type": str(event.get("aspect_type", "")),
        "strava_object_id": str(event.get("object_id", "")),
    }


def _event_from_key(event_key: str) -> dict | None:
    parts = event_key.split(":", 2)
    if len(parts) != 3:
        return None

    object_type, aspect_type, object_id = parts
    return {
        "object_type": object_type,
        "aspect_type": aspect_type,
        "object_id": object_id,
    }


def load_processed_events() -> set[str]:
    with database.get_session() as session:
        rows = session.query(ProcessedEvent).all()
        return {
            f"{row.object_type}:{row.aspect_type}:{row.strava_object_id}"
            for row in rows
        }


def save_processed_events(event_ids: set[str]) -> None:
    for event_key in event_ids:
        event = _event_from_key(event_key)
        if event:
            mark_event_as_processed(event)


def has_processed_event(event: dict) -> bool:
    identity = _event_identity(event)

    with database.get_session() as session:
        existing = (
            session.query(ProcessedEvent.id)
            .filter_by(**identity)
            .first()
        )
        return existing is not None


def mark_event_as_processed(
    event: dict,
    status: str = "processed",
    error_message: str | None = None,
) -> None:
    identity = _event_identity(event)

    processed_event = ProcessedEvent(
        **identity,
        status=status,
        error_message=error_message,
    )

    with database.get_session() as session:
        session.add(processed_event)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
