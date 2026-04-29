import importlib.util
import os
import sys
import types
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")


def install_stub_if_missing(module_name, module):
    if importlib.util.find_spec(module_name) is None:
        sys.modules[module_name] = module


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
install_stub_if_missing("dotenv", dotenv_stub)

openai_stub = types.ModuleType("openai")
openai_stub.OpenAI = lambda *args, **kwargs: object()
install_stub_if_missing("openai", openai_stub)

requests_stub = types.ModuleType("requests")
install_stub_if_missing("requests", requests_stub)

pytz_stub = types.ModuleType("pytz")
pytz_stub.timezone = lambda *args, **kwargs: None
install_stub_if_missing("pytz", pytz_stub)

from app.services.coaching_service import classify_ride
from app.utils.formatters import format_duration_pt_br, normalize_activity_name
from app.utils.storage import build_event_key


def activity(**overrides):
    data = {
        "distance_km": 25,
        "moving_time_min": 60,
        "elevation_gain_m": 200,
        "average_watts": None,
        "weighted_average_watts": None,
        "max_watts": None,
        "average_heartrate": None,
        "max_heartrate": None,
        "suffer_score": None,
        "pr_count": None,
        "achievement_count": None,
        "laps": [],
    }
    data.update(overrides)
    return data


class FormatterTests(unittest.TestCase):
    def test_format_duration_pt_br(self):
        self.assertEqual(format_duration_pt_br(35), "35min")
        self.assertEqual(format_duration_pt_br(60), "1h")
        self.assertEqual(format_duration_pt_br(77), "1h 17min")
        self.assertEqual(format_duration_pt_br(77.4), "1h 17min")

    def test_normalize_activity_name(self):
        self.assertEqual(normalize_activity_name("Morning Ride"), "Pedalada matinal")
        self.assertEqual(normalize_activity_name("Afternoon Ride"), "Pedalada da tarde")
        self.assertEqual(normalize_activity_name("Evening Ride"), "Pedalada noturna")
        self.assertEqual(normalize_activity_name("Treino livre"), "Treino livre")


class StorageTests(unittest.TestCase):
    def test_build_event_key_uses_stable_strava_fields(self):
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "event_time": 123456789,
        }

        self.assertEqual(build_event_key(event), "activity:create:18236736799")


class RideClassificationTests(unittest.TestCase):
    def test_classify_ride_intervalado_takes_priority(self):
        result = classify_ride(
            activity(
                distance_km=120,
                moving_time_min=240,
                elevation_gain_m=1500,
                weighted_average_watts=185,
            )
        )

        self.assertEqual(result, "intervalado")

    def test_classify_ride_by_distance_elevation_time_and_light_defaults(self):
        cases = [
            (activity(distance_km=100, moving_time_min=180), "longo"),
            (activity(distance_km=40, moving_time_min=90, elevation_gain_m=1000), "de escalada"),
            (activity(distance_km=20, moving_time_min=44), "curto"),
            (activity(distance_km=50, moving_time_min=90), "moderado"),
            (
                activity(
                    distance_km=30,
                    moving_time_min=70,
                    average_heartrate=110,
                    weighted_average_watts=120,
                ),
                "leve",
            ),
        ]

        for test_activity, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_ride(test_activity), expected)

    def test_classify_ride_detects_hard_laps(self):
        result = classify_ride(
            activity(
                laps=[
                    {"average_watts": 181},
                    {"average_heartrate": 161},
                ]
            )
        )

        self.assertEqual(result, "intervalado")


if __name__ == "__main__":
    unittest.main()
