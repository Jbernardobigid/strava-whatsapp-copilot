import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from fastapi.responses import RedirectResponse

from app.routes.strava import connect_strava, debug_strava_token_status
from app.services import strava_service
from app.utils import storage


class StravaRouteTests(unittest.TestCase):
    def test_connect_strava_redirects_to_authorization_url(self):
        original = strava_service.STRAVA_CLIENT_ID, strava_service.STRAVA_REDIRECT_URI
        strava_service.STRAVA_CLIENT_ID = "12345"
        strava_service.STRAVA_REDIRECT_URI = "https://example.com/strava/callback"

        try:
            response = connect_strava()
        finally:
            strava_service.STRAVA_CLIENT_ID, strava_service.STRAVA_REDIRECT_URI = original

        self.assertIsInstance(response, RedirectResponse)
        self.assertEqual(response.status_code, 307)
        self.assertIn("https://www.strava.com/oauth/authorize", response.headers["location"])
        self.assertIn("client_id=12345", response.headers["location"])
        self.assertIn("response_type=code", response.headers["location"])

    def test_token_status_endpoint_returns_safe_metadata_only(self):
        original = storage.get_strava_token_status
        storage.get_strava_token_status = lambda: {
            "token_exists": True,
            "athlete_id": "12345",
            "expires_at": 1234567890,
            "is_expired": True,
            "storage_type": "database",
        }

        try:
            response = debug_strava_token_status()
        finally:
            storage.get_strava_token_status = original

        self.assertEqual(response["token_exists"], True)
        self.assertEqual(response["athlete_id"], "12345")
        self.assertEqual(response["storage_type"], "database")
        self.assertNotIn("access_token", response)
        self.assertNotIn("refresh_token", response)


if __name__ == "__main__":
    unittest.main()
