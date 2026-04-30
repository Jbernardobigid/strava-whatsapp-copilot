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


class StubRedirectResponse:
    def __init__(self, url, status_code=307):
        self.status_code = status_code
        self.headers = {"location": url}


fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.__path__ = []
fastapi_stub.APIRouter = StubAPIRouter
fastapi_stub.Request = object
install_stub_if_missing("fastapi", fastapi_stub)
if "fastapi" in sys.modules:
    sys.modules["fastapi"].APIRouter = StubAPIRouter
    sys.modules["fastapi"].Request = object

responses_stub = types.ModuleType("fastapi.responses")
responses_stub.RedirectResponse = StubRedirectResponse
if "fastapi.responses" not in sys.modules:
    sys.modules["fastapi.responses"] = responses_stub

twilio_stub = types.ModuleType("twilio")
twilio_stub.__path__ = []
install_stub_if_missing("twilio", twilio_stub)

rest_stub = types.ModuleType("twilio.rest")
rest_stub.Client = lambda *args, **kwargs: object()
if "twilio.rest" not in sys.modules:
    sys.modules["twilio.rest"] = rest_stub

from app.routes import strava as strava_routes
from app.routes.strava import connect_strava, debug_strava_token_status
from app.services import strava_service


class StravaRouteTests(unittest.TestCase):
    def test_connect_strava_redirects_to_authorization_url(self):
        original = strava_service.STRAVA_CLIENT_ID, strava_service.STRAVA_REDIRECT_URI
        strava_service.STRAVA_CLIENT_ID = "12345"
        strava_service.STRAVA_REDIRECT_URI = "https://example.com/strava/callback"

        try:
            response = connect_strava()
        finally:
            strava_service.STRAVA_CLIENT_ID, strava_service.STRAVA_REDIRECT_URI = original

        self.assertEqual(response.status_code, 307)
        self.assertIn("location", response.headers)
        self.assertIn("https://www.strava.com/oauth/authorize", response.headers["location"])
        self.assertIn("client_id=12345", response.headers["location"])
        self.assertIn("response_type=code", response.headers["location"])

    def test_token_status_endpoint_returns_safe_metadata_only(self):
        original = strava_routes.get_strava_token_status
        strava_routes.get_strava_token_status = lambda: {
            "token_exists": True,
            "athlete_id": "12345",
            "expires_at": 1234567890,
            "is_expired": True,
            "storage_type": "database",
        }

        try:
            response = debug_strava_token_status()
        finally:
            strava_routes.get_strava_token_status = original

        self.assertEqual(response["token_exists"], True)
        self.assertEqual(response["athlete_id"], "12345")
        self.assertEqual(response["storage_type"], "database")
        self.assertNotIn("access_token", response)
        self.assertNotIn("refresh_token", response)


if __name__ == "__main__":
    unittest.main()
