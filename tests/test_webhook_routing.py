import asyncio
import importlib.util
import os
import sys
import types
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")


def install_stub_if_missing(module_name, module):
    if module_name in sys.modules:
        return
    if importlib.util.find_spec(module_name) is None:
        sys.modules[module_name] = module


class StubAPIRouter:
    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class StubJSONResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


def stub_query(default=None, alias=None):
    return default


fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.__path__ = []
fastapi_stub.APIRouter = StubAPIRouter
fastapi_stub.Query = stub_query
fastapi_stub.Request = object
install_stub_if_missing("fastapi", fastapi_stub)
if "fastapi" in sys.modules:
    sys.modules["fastapi"].APIRouter = StubAPIRouter
    sys.modules["fastapi"].Query = stub_query
    sys.modules["fastapi"].Request = object

responses_stub = types.ModuleType("fastapi.responses")
responses_stub.JSONResponse = StubJSONResponse
if "fastapi.responses" not in sys.modules:
    sys.modules["fastapi.responses"] = responses_stub
else:
    sys.modules["fastapi.responses"].JSONResponse = StubJSONResponse

twilio_stub = types.ModuleType("twilio")
twilio_stub.__path__ = []
install_stub_if_missing("twilio", twilio_stub)

rest_stub = types.ModuleType("twilio.rest")
rest_stub.Client = lambda *args, **kwargs: object()
if "twilio.rest" not in sys.modules:
    sys.modules["twilio.rest"] = rest_stub

from app.routes import webhook as webhook_routes


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class WebhookOwnerRoutingTests(unittest.TestCase):
    def test_webhook_routes_owner_to_user_token_and_whatsapp_destination(self):
        calls = {}
        original = (
            webhook_routes.has_processed_event,
            webhook_routes.resolve_app_user_for_webhook_event,
            webhook_routes.get_strava_activity_by_id,
            webhook_routes.build_activity_message,
            webhook_routes.send_whatsapp_message,
            webhook_routes.mark_event_as_processed,
        )
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "owner_id": 12345,
        }
        activity = {
            "id": 18236736799,
            "name": "Morning Ride",
            "distance_km": 42.0,
            "moving_time_min": 90,
            "elevation_gain_m": 350,
            "type": "Ride",
        }

        webhook_routes.has_processed_event = lambda payload: False
        webhook_routes.resolve_app_user_for_webhook_event = lambda payload: {
            "id": 7,
            "strava_athlete_id": "12345",
            "whatsapp_number": "whatsapp:+5511999991234",
        }

        def fake_get_activity(activity_id, user_id=None, athlete_id=None):
            calls["get_activity"] = (activity_id, user_id, athlete_id)
            return activity, None

        def fake_build_message(payload, user_id=None, athlete_id=None):
            calls["build_message"] = (payload, user_id, athlete_id)
            return "mensagem"

        def fake_send(body, to_number=None, user_id=None, strava_activity_id=None):
            calls["send"] = (body, to_number, user_id, strava_activity_id)
            return "SM123"

        def fake_mark(payload, user_id=None):
            calls["mark"] = (payload, user_id)

        webhook_routes.get_strava_activity_by_id = fake_get_activity
        webhook_routes.build_activity_message = fake_build_message
        webhook_routes.send_whatsapp_message = fake_send
        webhook_routes.mark_event_as_processed = fake_mark

        try:
            response = asyncio.run(webhook_routes.receive_strava_webhook(FakeRequest(event)))
        finally:
            (
                webhook_routes.has_processed_event,
                webhook_routes.resolve_app_user_for_webhook_event,
                webhook_routes.get_strava_activity_by_id,
                webhook_routes.build_activity_message,
                webhook_routes.send_whatsapp_message,
                webhook_routes.mark_event_as_processed,
            ) = original

        self.assertEqual(response, {"received": True})
        self.assertEqual(calls["get_activity"], (18236736799, 7, "12345"))
        self.assertEqual(calls["build_message"], (activity, 7, "12345"))
        self.assertEqual(
            calls["send"],
            ("mensagem", "whatsapp:+5511999991234", 7, 18236736799),
        )
        self.assertEqual(calls["mark"], (event, 7))

    def test_unknown_webhook_owner_is_skipped_safely(self):
        original = (
            webhook_routes.has_processed_event,
            webhook_routes.resolve_app_user_for_webhook_event,
            webhook_routes.get_strava_activity_by_id,
            webhook_routes.send_whatsapp_message,
        )
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
            "owner_id": 67890,
        }

        webhook_routes.has_processed_event = lambda payload: False
        webhook_routes.resolve_app_user_for_webhook_event = lambda payload: None
        webhook_routes.get_strava_activity_by_id = lambda *args, **kwargs: self.fail(
            "unknown owner should not fetch activity"
        )
        webhook_routes.send_whatsapp_message = lambda *args, **kwargs: self.fail(
            "unknown owner should not send WhatsApp"
        )

        try:
            response = asyncio.run(webhook_routes.receive_strava_webhook(FakeRequest(event)))
        finally:
            (
                webhook_routes.has_processed_event,
                webhook_routes.resolve_app_user_for_webhook_event,
                webhook_routes.get_strava_activity_by_id,
                webhook_routes.send_whatsapp_message,
            ) = original

        self.assertEqual(response, {"received": True, "skipped": "unknown_owner"})
        self.assertNotIn("access_token", response)
        self.assertNotIn("refresh_token", response)
        self.assertNotIn("whatsapp_number", response)

    def test_webhook_preserves_default_fallback_when_owner_id_is_absent(self):
        calls = {}
        original = (
            webhook_routes.has_processed_event,
            webhook_routes.resolve_app_user_for_webhook_event,
            webhook_routes.get_strava_activity_by_id,
            webhook_routes.build_activity_message,
            webhook_routes.send_whatsapp_message,
            webhook_routes.mark_event_as_processed,
        )
        event = {
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 18236736799,
        }
        activity = {
            "id": 18236736799,
            "name": "Morning Ride",
            "distance_km": 42.0,
            "moving_time_min": 90,
            "elevation_gain_m": 350,
            "type": "Ride",
        }

        webhook_routes.has_processed_event = lambda payload: False
        webhook_routes.resolve_app_user_for_webhook_event = lambda payload: None

        def fake_get_activity(activity_id, user_id=None, athlete_id=None):
            calls["get_activity"] = (activity_id, user_id, athlete_id)
            return activity, None

        def fake_send(body, to_number=None, user_id=None, strava_activity_id=None):
            calls["send"] = (body, to_number, user_id, strava_activity_id)
            return "SM123"

        webhook_routes.get_strava_activity_by_id = fake_get_activity
        webhook_routes.build_activity_message = lambda payload, **kwargs: "mensagem"
        webhook_routes.send_whatsapp_message = fake_send
        webhook_routes.mark_event_as_processed = lambda payload, user_id=None: calls.setdefault(
            "mark",
            (payload, user_id),
        )

        try:
            response = asyncio.run(webhook_routes.receive_strava_webhook(FakeRequest(event)))
        finally:
            (
                webhook_routes.has_processed_event,
                webhook_routes.resolve_app_user_for_webhook_event,
                webhook_routes.get_strava_activity_by_id,
                webhook_routes.build_activity_message,
                webhook_routes.send_whatsapp_message,
                webhook_routes.mark_event_as_processed,
            ) = original

        self.assertEqual(response, {"received": True})
        self.assertEqual(calls["get_activity"], (18236736799, None, None))
        self.assertEqual(calls["send"], ("mensagem", None, None, 18236736799))
        self.assertEqual(calls["mark"], (event, None))


if __name__ == "__main__":
    unittest.main()
