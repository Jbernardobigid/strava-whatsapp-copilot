import json
import time

from sqlalchemy.exc import IntegrityError

from app import database
from app.config import PROCESSED_EVENTS_FILE, TOKEN_FILE, YOUR_WHATSAPP_NUMBER
from app.models import AppUser, ProcessedEvent, SentMessage, StravaToken
from app.utils.logger import get_logger

DEFAULT_USER_NAME = "Default user"
logger = get_logger(__name__)


def _database_enabled() -> bool:
    return database.is_database_configured()


def _load_json_file(path) -> dict | list | None:
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None

    return json.loads(content)


def mask_whatsapp_number(number: str | None) -> str | None:
    if not number:
        return None

    value = str(number)
    prefix = ""
    local_value = value

    if ":" in value:
        prefix, local_value = value.split(":", 1)
        prefix = f"{prefix}:"

    if len(local_value) <= 4:
        return f"{prefix}{local_value}"

    return f"{prefix}{'*' * (len(local_value) - 4)}{local_value[-4:]}"


def _app_user_snapshot(user: AppUser | None) -> dict | None:
    if not user:
        return None

    return {
        "id": user.id,
        "name": user.name,
        "whatsapp_number": user.whatsapp_number,
        "strava_athlete_id": user.strava_athlete_id,
    }


def _ensure_default_whatsapp_number(user: AppUser) -> None:
    if YOUR_WHATSAPP_NUMBER and not user.whatsapp_number:
        user.whatsapp_number = YOUR_WHATSAPP_NUMBER


def _get_or_create_user_for_athlete(
    session,
    athlete_id: str | int | None = None,
) -> AppUser:
    athlete_id = str(athlete_id) if athlete_id else None
    user = None

    if athlete_id:
        user = session.query(AppUser).filter_by(strava_athlete_id=athlete_id).first()
        if user:
            _ensure_default_whatsapp_number(user)
            session.flush()
            return user

    first_user = session.query(AppUser).order_by(AppUser.id).first()

    if not athlete_id:
        if first_user:
            _ensure_default_whatsapp_number(first_user)
            session.flush()
            return first_user

        user = AppUser(
            name=DEFAULT_USER_NAME,
            whatsapp_number=YOUR_WHATSAPP_NUMBER,
        )
        session.add(user)
        session.flush()
        return user

    if first_user and not first_user.strava_athlete_id:
        first_user.strava_athlete_id = athlete_id
        _ensure_default_whatsapp_number(first_user)
        session.flush()
        return first_user

    if not first_user:
        user = AppUser(
            name=DEFAULT_USER_NAME,
            whatsapp_number=YOUR_WHATSAPP_NUMBER,
            strava_athlete_id=athlete_id,
        )
        session.add(user)
        session.flush()
        return user

    user = AppUser(
        name=f"Strava athlete {athlete_id}",
        whatsapp_number=YOUR_WHATSAPP_NUMBER,
        strava_athlete_id=athlete_id,
    )
    session.add(user)
    session.flush()
    return user


def _get_or_create_default_user(session, athlete_id: str | None = None) -> AppUser:
    return _get_or_create_user_for_athlete(session, athlete_id=athlete_id)


def get_or_create_app_user_for_athlete(athlete_id: str | int | None) -> dict | None:
    if not _database_enabled():
        return None

    with database.get_session() as session:
        user = _get_or_create_user_for_athlete(session, athlete_id=athlete_id)
        session.commit()
        session.refresh(user)
        return _app_user_snapshot(user)


def get_app_user_by_strava_athlete_id(athlete_id: str | int | None) -> dict | None:
    if not _database_enabled() or not athlete_id:
        return None

    with database.get_session() as session:
        user = (
            session.query(AppUser)
            .filter_by(strava_athlete_id=str(athlete_id))
            .first()
        )

        if user:
            _ensure_default_whatsapp_number(user)
            session.commit()
            session.refresh(user)

        return _app_user_snapshot(user)


def get_default_app_user() -> dict | None:
    if not _database_enabled():
        return None

    with database.get_session() as session:
        user = session.query(AppUser).order_by(AppUser.id).first()

        if user:
            _ensure_default_whatsapp_number(user)
            session.commit()
            session.refresh(user)

        return _app_user_snapshot(user)


def resolve_app_user_for_webhook_event(event: dict) -> dict | None:
    if not _database_enabled():
        return None

    owner_id = event.get("owner_id")

    with database.get_session() as session:
        if owner_id:
            owner_id = str(owner_id)
            user = session.query(AppUser).filter_by(strava_athlete_id=owner_id).first()
            if user:
                _ensure_default_whatsapp_number(user)
                session.commit()
                session.refresh(user)
                return _app_user_snapshot(user)

            fallback_user = session.query(AppUser).order_by(AppUser.id).first()
            if fallback_user and not fallback_user.strava_athlete_id:
                fallback_user.strava_athlete_id = owner_id
                _ensure_default_whatsapp_number(fallback_user)
                session.commit()
                session.refresh(fallback_user)
                return _app_user_snapshot(fallback_user)

            logger.warning(
                "No app user mapped for Strava webhook owner_id=%s",
                owner_id,
            )
            return None

        fallback_user = session.query(AppUser).order_by(AppUser.id).first()
        if fallback_user:
            _ensure_default_whatsapp_number(fallback_user)
            session.commit()
            session.refresh(fallback_user)
            return _app_user_snapshot(fallback_user)

        return None


def _get_default_user_id_for_event(session, event: dict) -> int | None:
    owner_id = event.get("owner_id")
    if not owner_id:
        return None

    user = session.query(AppUser).filter_by(strava_athlete_id=str(owner_id)).first()
    return user.id if user else None


def _token_status_from_data(
    token_data: dict | None,
    storage_type: str,
) -> dict:
    if not token_data:
        return {
            "token_exists": False,
            "athlete_id": None,
            "expires_at": None,
            "is_expired": None,
            "storage_type": storage_type,
        }

    expires_at = token_data.get("expires_at")
    athlete = token_data.get("athlete") or {}
    athlete_id = token_data.get("athlete_id") or athlete.get("id")

    is_expired = None
    if expires_at is not None:
        is_expired = int(time.time()) >= int(expires_at)

    return {
        "token_exists": True,
        "athlete_id": str(athlete_id) if athlete_id else None,
        "expires_at": expires_at,
        "is_expired": is_expired,
        "storage_type": storage_type,
    }


def _sent_message_result(row: SentMessage | None, updated: bool) -> dict:
    return {
        "updated": updated,
        "message_found": row is not None,
        "status": row.status if row else None,
        "error_code": row.error_code if row else None,
    }


def save_strava_tokens(token_data: dict, user_id: int | None = None) -> None:
    if not _database_enabled():
        TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        return

    athlete = token_data.get("athlete") or {}
    athlete_id = athlete.get("id") or token_data.get("athlete_id")
    athlete_id = str(athlete_id) if athlete_id else None

    with database.get_session() as session:
        user = session.get(AppUser, user_id) if user_id else None
        if not user:
            user = _get_or_create_user_for_athlete(session, athlete_id=athlete_id)
        else:
            _ensure_default_whatsapp_number(user)
            if athlete_id and user.strava_athlete_id != athlete_id:
                user.strava_athlete_id = athlete_id
            session.flush()

        token = session.query(StravaToken).filter_by(user_id=user.id).first()

        if not token:
            token = StravaToken(user_id=user.id)
            session.add(token)

        token.athlete_id = athlete_id or token.athlete_id or user.strava_athlete_id
        token.access_token = token_data["access_token"]
        token.refresh_token = token_data["refresh_token"]
        token.expires_at = token_data["expires_at"]

        session.commit()


def load_strava_tokens(
    user_id: int | None = None,
    athlete_id: str | int | None = None,
) -> dict | None:
    if not _database_enabled():
        token_data = _load_json_file(TOKEN_FILE)
        return token_data if isinstance(token_data, dict) else None

    with database.get_session() as session:
        query = session.query(StravaToken)

        if user_id is not None:
            token = query.filter_by(user_id=user_id).first()
        elif athlete_id is not None:
            token = query.filter_by(athlete_id=str(athlete_id)).first()
        else:
            token = query.order_by(StravaToken.id.desc()).first()

        if not token:
            return None

        athlete = {"id": token.athlete_id} if token.athlete_id else {}
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "athlete": athlete,
            "user_id": token.user_id,
        }


def get_strava_token_status() -> dict:
    if not _database_enabled():
        token_data = _load_json_file(TOKEN_FILE)
        return _token_status_from_data(
            token_data if isinstance(token_data, dict) else None,
            "json_file",
        )

    with database.get_session() as session:
        token = session.query(StravaToken).order_by(StravaToken.id.desc()).first()

        if not token:
            return _token_status_from_data(None, "database")

        return _token_status_from_data(
            {
                "athlete_id": token.athlete_id,
                "expires_at": token.expires_at,
            },
            "database",
        )


def record_sent_message(
    twilio_message_sid: str,
    to_number: str | None = None,
    status: str = "accepted",
    user_id: int | None = None,
    strava_activity_id: str | int | None = None,
) -> dict | None:
    if not _database_enabled():
        logger.warning(
            "DATABASE_URL not configured; skipping sent message persistence"
        )
        return None

    try:
        with database.get_session() as session:
            row = (
                session.query(SentMessage)
                .filter_by(twilio_message_sid=twilio_message_sid)
                .first()
            )

            if not row:
                row = SentMessage(twilio_message_sid=twilio_message_sid)
                session.add(row)

            row.user_id = user_id
            row.strava_activity_id = (
                str(strava_activity_id) if strava_activity_id is not None else None
            )
            row.to_number = mask_whatsapp_number(to_number)
            row.status = status or "accepted"

            session.commit()
            session.refresh(row)
            return _sent_message_result(row, updated=True)
    except Exception as exc:
        logger.warning(
            "Unable to persist Twilio sent message metadata: %s",
            exc.__class__.__name__,
        )
        return None


def update_sent_message_status(
    twilio_message_sid: str | None,
    status: str | None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict:
    if not twilio_message_sid:
        return {
            "updated": False,
            "message_found": False,
            "status": status,
            "error_code": error_code,
        }

    if not _database_enabled():
        logger.warning(
            "DATABASE_URL not configured; skipping Twilio status persistence"
        )
        return {
            "updated": False,
            "message_found": False,
            "status": status,
            "error_code": error_code,
        }

    try:
        with database.get_session() as session:
            row = (
                session.query(SentMessage)
                .filter_by(twilio_message_sid=twilio_message_sid)
                .first()
            )

            if not row:
                return _sent_message_result(None, updated=False)

            if status:
                row.status = status
            row.error_code = error_code
            row.error_message = error_message

            session.commit()
            session.refresh(row)
            return _sent_message_result(row, updated=True)
    except Exception as exc:
        logger.warning(
            "Unable to update Twilio sent message status: %s",
            exc.__class__.__name__,
        )
        return {
            "updated": False,
            "message_found": False,
            "status": status,
            "error_code": error_code,
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
    user_id: int | None = None,
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
            user_id=user_id if user_id is not None else _get_default_user_id_for_event(session, event),
            status=status,
            error_message=error_message,
        )

        session.add(processed_event)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
