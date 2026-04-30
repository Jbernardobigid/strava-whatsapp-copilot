import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import database
from app.models import AppUser, Base, ProcessedEvent, StravaToken
from app.utils.storage import (
    get_strava_token_status,
    has_processed_event,
    load_strava_tokens,
    mark_event_as_processed,
    save_strava_tokens,
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


if __name__ == "__main__":
    unittest.main()
