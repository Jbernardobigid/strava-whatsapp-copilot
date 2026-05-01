import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import database
from app.models import AppUser, Base, ProcessedEvent, SentMessage, StravaToken
from app.utils.storage import (
    get_app_user_by_strava_athlete_id,
    get_or_create_app_user_for_athlete,
    get_strava_token_status,
    has_processed_event,
    load_strava_tokens,
    mark_event_as_processed,
    mask_whatsapp_number,
    record_sent_message,
    resolve_app_user_for_webhook_event,
    save_strava_tokens,
    update_sent_message_status,
)


class DatabaseStorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database._engine = self.engine
        database.SessionLocal.configure(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        database._engine = None

    def test_same_strava_event_is_only_recorded_once(self):
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "event_time": 123456789,
        }
        duplicate_delivery = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "event_time": 987654321,
        }

        self.assertFalse(has_processed_event(event))

        mark_event_as_processed(event)

        self.assertTrue(has_processed_event(event))
        self.assertTrue(has_processed_event(duplicate_delivery))

        mark_event_as_processed(duplicate_delivery)

        with database.get_session() as session:
            rows = session.query(ProcessedEvent).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].strava_object_id, "18236736799")
        self.assertEqual(rows[0].object_type, "activity")
        self.assertEqual(rows[0].aspect_type, "create")
        self.assertEqual(rows[0].status, "processed")

    def test_strava_tokens_are_saved_for_default_user(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )

        token_data = load_strava_tokens()

        self.assertEqual(token_data["access_token"], "access-token-1")
        self.assertEqual(token_data["refresh_token"], "refresh-token-1")
        self.assertEqual(token_data["expires_at"], 1234567890)
        self.assertEqual(token_data["athlete"], {"id": "12345"})

        with database.get_session() as session:
            users = session.query(AppUser).all()
            tokens = session.query(StravaToken).all()

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].name, "Default user")
        self.assertEqual(users[0].strava_athlete_id, "12345")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].user_id, users[0].id)
        self.assertEqual(tokens[0].athlete_id, "12345")

    def test_user_lookup_by_strava_athlete_id(self):
        user = get_or_create_app_user_for_athlete(12345)
        found = get_app_user_by_strava_athlete_id("12345")

        self.assertEqual(found["id"], user["id"])
        self.assertEqual(found["strava_athlete_id"], "12345")

    def test_new_athlete_creates_new_user_without_rewriting_existing_user(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )
        save_strava_tokens(
            {
                "access_token": "access-token-2",
                "refresh_token": "refresh-token-2",
                "expires_at": 1234567891,
                "athlete": {"id": 67890},
            }
        )

        with database.get_session() as session:
            athlete_ids = sorted(user.strava_athlete_id for user in session.query(AppUser).all())

        self.assertEqual(athlete_ids, ["12345", "67890"])

    def test_token_refresh_updates_existing_database_record(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )
        save_strava_tokens(
            {
                "access_token": "access-token-2",
                "refresh_token": "refresh-token-2",
                "expires_at": 2234567890,
            }
        )

        token_data = load_strava_tokens()

        self.assertEqual(token_data["access_token"], "access-token-2")
        self.assertEqual(token_data["refresh_token"], "refresh-token-2")
        self.assertEqual(token_data["expires_at"], 2234567890)

        with database.get_session() as session:
            self.assertEqual(session.query(AppUser).count(), 1)
            self.assertEqual(session.query(StravaToken).count(), 1)

    def test_load_strava_tokens_can_select_by_user_or_athlete(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )
        user = get_app_user_by_strava_athlete_id(12345)

        by_user = load_strava_tokens(user_id=user["id"])
        by_athlete = load_strava_tokens(athlete_id=12345)

        self.assertEqual(by_user["access_token"], "access-token-1")
        self.assertEqual(by_athlete["access_token"], "access-token-1")
        self.assertEqual(by_user["user_id"], user["id"])

    def test_processed_event_links_to_user_when_owner_id_matches(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "owner_id": 12345,
        }

        mark_event_as_processed(event)

        with database.get_session() as session:
            user = session.query(AppUser).one()
            processed_event = session.query(ProcessedEvent).one()

        self.assertEqual(processed_event.user_id, user.id)

    def test_processed_event_can_use_explicit_user_id(self):
        user = get_or_create_app_user_for_athlete(12345)
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "owner_id": 12345,
        }

        mark_event_as_processed(event, user_id=user["id"])

        with database.get_session() as session:
            processed_event = session.query(ProcessedEvent).one()

        self.assertEqual(processed_event.user_id, user["id"])

    def test_resolve_webhook_owner_uses_mapped_user(self):
        user = get_or_create_app_user_for_athlete(12345)

        resolved = resolve_app_user_for_webhook_event({"owner_id": 12345})

        self.assertEqual(resolved["id"], user["id"])
        self.assertEqual(resolved["strava_athlete_id"], "12345")

    def test_resolve_webhook_owner_falls_back_for_unmapped_default_user(self):
        with database.get_session() as session:
            session.add(AppUser(name="Default user"))
            session.commit()

        resolved = resolve_app_user_for_webhook_event({"owner_id": 12345})

        self.assertEqual(resolved["strava_athlete_id"], "12345")

    def test_resolve_webhook_owner_returns_none_for_unknown_mapped_user(self):
        get_or_create_app_user_for_athlete(12345)

        resolved = resolve_app_user_for_webhook_event({"owner_id": 67890})

        self.assertIsNone(resolved)

    def test_token_status_returns_metadata_without_secrets(self):
        save_strava_tokens(
            {
                "access_token": "access-token-1",
                "refresh_token": "refresh-token-1",
                "expires_at": 1234567890,
                "athlete": {"id": 12345},
            }
        )

        status = get_strava_token_status()

        self.assertEqual(
            status,
            {
                "token_exists": True,
                "athlete_id": "12345",
                "expires_at": 1234567890,
                "is_expired": True,
                "storage_type": "database",
            },
        )
        self.assertNotIn("access_token", status)
        self.assertNotIn("refresh_token", status)
        self.assertNotIn("whatsapp_number", status)

    def test_record_sent_message_masks_number_and_persists_status(self):
        user = get_or_create_app_user_for_athlete(12345)
        result = record_sent_message(
            twilio_message_sid="SM123",
            to_number="whatsapp:+5511999991234",
            status="queued",
            user_id=user["id"],
            strava_activity_id=18236736799,
        )

        self.assertEqual(result["updated"], True)
        self.assertEqual(result["message_found"], True)
        self.assertEqual(result["status"], "queued")

        with database.get_session() as session:
            row = session.query(SentMessage).one()

        self.assertEqual(row.twilio_message_sid, "SM123")
        self.assertEqual(row.user_id, user["id"])
        self.assertEqual(row.strava_activity_id, "18236736799")
        self.assertEqual(row.to_number, "whatsapp:**********1234")
        self.assertNotEqual(row.to_number, "whatsapp:+5511999991234")

    def test_update_sent_message_status_from_callback_payload(self):
        record_sent_message(
            twilio_message_sid="SM123",
            to_number="whatsapp:+5511999991234",
            status="queued",
        )

        result = update_sent_message_status(
            twilio_message_sid="SM123",
            status="delivered",
            error_code=None,
            error_message=None,
        )

        self.assertEqual(result["updated"], True)
        self.assertEqual(result["message_found"], True)
        self.assertEqual(result["status"], "delivered")

        with database.get_session() as session:
            row = session.query(SentMessage).one()

        self.assertEqual(row.status, "delivered")
        self.assertIsNone(row.error_code)
        self.assertIsNone(row.error_message)

    def test_mask_whatsapp_number_preserves_only_last_four_digits(self):
        self.assertEqual(
            mask_whatsapp_number("whatsapp:+5511999991234"),
            "whatsapp:**********1234",
        )


if __name__ == "__main__":
    unittest.main()
