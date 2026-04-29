import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import database
from app.models import Base, ProcessedEvent
from app.utils.storage import has_processed_event, mark_event_as_processed


class DuplicateEventStorageTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
