import json

from sqlalchemy.exc import IntegrityError

from app import database
from app.config import PROCESSED_EVENTS_FILE, TOKEN_FILE, YOUR_WHATSAPP_NUMBER
from app.models import AppUser, ProcessedEvent, StravaToken

DEFAULT_USER_NAME = "Default user"


def _database_enabled() -> bool:
    return database.is_database_configured()


def _load_json_file(path) -> dict | list | None:
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None

    return json.loads(content)


def _get_or_create_default_user(session, athlete_id: str | None = None) -> AppUser:
    user = None

    if athlete_id:
        user = session.query(AppUser).filter_by(strava_athlete_id=athlete_id).first()

    if not user:
        user = session.query(AppUser).order_by(AppUser.id).first()

    if not user:
        user = AppUser(
            name=DEFAULT_USER_NAME,
            whatsapp_number=YOUR_WHATSAPP_NUMBER,
            strava_athlete_id=athlete_id,
        )
        session.add(user)
        session.flush()
        return user

    if athlete_id and user.strava_athlete_id != athlete_id:
        user.strava_athlete_id = athlete_id

    if YOUR_WHATSAPP_NUMBER and not user.whatsapp_number:
        user.whatsapp_number = YOUR_WHATSAPP_NUMBER

    session.flush()
    return user


def _get_default_user_id_for_event(session, event: dict) -> int | None:
    owner_id = event.get("owner_id")
    if not owner_id:
        return None

    user = session.query(AppUser).filter_by(strava_athlete_id=str(owner_id)).first()
    return user.id if user else None


def save_strava_tokens(token_data: dict) -> None:
    if not _database_enabled():
        TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        return

    athlete = token_data.get("athlete") or {}
    athlete_id = athlete.get("id") or token_data.get("athlete_id")
    athlete_id = str(athlete_id) if athlete_id else None

    with database.get_session() as session:
        user = _get_or_create_default_user(session, athlete_id=athlete_id)
        token = session.query(StravaToken).filter_by(user_id=user.id).first()

        if not token:
            token = StravaToken(user_id=user.id)
            session.add(token)

        token.athlete_id = athlete_id or token.athlete_id or user.strava_athlete_id
        token.access_token = token_data["access_token"]
        token.refresh_token = token_data["refresh_token"]
        token.expires_at = token_data["expires_at"]

        session.commit()


def load_strava_tokens() -> dict | None:
    if not _database_enabled():
        token_data = _load_json_file(TOKEN_FILE)
        return token_data if isinstance(token_data, dict) else None

    with database.get_session() as session:
        token = session.query(StravaToken).order_by(StravaToken.id.desc()).first()

        if not token:
            return None

        athlete = {"id": token.athlete_id} if token.athlete_id else {}
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "athlete": athlete,
        }


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
    if not _database_enabled():
        event_ids = _load_json_file(PROCESSED_EVENTS_FILE)
        return set(event_ids) if isinstance(event_ids, list) else set()

    with database.get_session() as session:
        rows = session.query(ProcessedEvent).all()
        return {
            f"{row.object_type}:{row.aspect_type}:{row.strava_object_id}"
            for row in rows
        }


def save_processed_events(event_ids: set[str]) -> None:
    if not _database_enabled():
        PROCESSED_EVENTS_FILE.write_text(
            json.dumps(sorted(event_ids), indent=2),
            encoding="utf-8",
        )
        return

    for event_key in event_ids:
        event = _event_from_key(event_key)
        if event:
            mark_event_as_processed(event)


def has_processed_event(event: dict) -> bool:
    if not _database_enabled():
        return build_event_key(event) in load_processed_events()

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
    if not _database_enabled():
        processed = load_processed_events()
        processed.add(build_event_key(event))
        save_processed_events(processed)
        return

    identity = _event_identity(event)

    with database.get_session() as session:
        processed_event = ProcessedEvent(
            **identity,
            user_id=_get_default_user_id_for_event(session, event),
            status=status,
            error_message=error_message,
        )

        session.add(processed_event)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
