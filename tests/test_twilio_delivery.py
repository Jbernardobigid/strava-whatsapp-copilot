import asyncio
import importlib.util
import os
import sys
import types
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import database
from app.models import Base, SentMessage


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


fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.__path__ = []
fastapi_stub.APIRouter = StubAPIRouter
fastapi_stub.Request = object
install_stub_if_missing("fastapi", fastapi_stub)
if "fastapi" in sys.modules:
    sys.modules["fastapi"].APIRouter = StubAPIRouter
    sys.modules["fastapi"].Request = object


class FakeMessage:
    sid = "SM456"
    status = "queued"


class FakeMessages:
    def create(self, body, from_, to):
        self.body = body
        self.from_ = from_
        self.to = to
        return FakeMessage()


class FakeClient:
    def __init__(self, account_sid, auth_token):
        self.messages = FakeMessages()


twilio_stub = types.ModuleType("twilio")
twilio_stub.__path__ = []
install_stub_if_missing("twilio", twilio_stub)

rest_stub = types.ModuleType("twilio.rest")
rest_stub.Client = FakeClient
if "twilio.rest" not in sys.modules:
    sys.modules["twilio.rest"] = rest_stub

from app.routes.twilio import twilio_status_callback
from app.services import whatsapp_service
from app.utils.storage import record_sent_message


class FakeRequest:
    def __init__(self, form_data):
        self.form_data = form_data

    async def form(self):
        return self.form_data


class TwilioDeliveryTests(unittest.TestCase):
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

    def test_send_whatsapp_message_persists_queued_sent_message(self):
        original_config = (
            whatsapp_service.TWILIO_ACCOUNT_SID,
            whatsapp_service.TWILIO_AUTH_TOKEN,
            whatsapp_service.TWILIO_WHATSAPP_NUMBER,
            whatsapp_service.YOUR_WHATSAPP_NUMBER,
            whatsapp_service.Client,
        )
        whatsapp_service.TWILIO_ACCOUNT_SID = "AC123"
        whatsapp_service.TWILIO_AUTH_TOKEN = "auth-token"
        whatsapp_service.TWILIO_WHATSAPP_NUMBER = "whatsapp:+15550000000"
        whatsapp_service.YOUR_WHATSAPP_NUMBER = "whatsapp:+5511999991234"
        whatsapp_service.Client = FakeClient

        try:
            sid = whatsapp_service.send_whatsapp_message("Mensagem de teste")
        finally:
            (
                whatsapp_service.TWILIO_ACCOUNT_SID,
                whatsapp_service.TWILIO_AUTH_TOKEN,
                whatsapp_service.TWILIO_WHATSAPP_NUMBER,
                whatsapp_service.YOUR_WHATSAPP_NUMBER,
                whatsapp_service.Client,
            ) = original_config

        self.assertEqual(sid, "SM456")

        with database.get_session() as session:
            row = session.query(SentMessage).one()

        self.assertEqual(row.twilio_message_sid, "SM456")
        self.assertEqual(row.status, "queued")
        self.assertEqual(row.to_number, "whatsapp:**********1234")
        self.assertNotEqual(row.to_number, "whatsapp:+5511999991234")

    def test_twilio_status_callback_updates_message_without_returning_secrets(self):
        record_sent_message(
            twilio_message_sid="SM123",
            to_number="whatsapp:+5511999991234",
            status="queued",
        )
        request = FakeRequest(
            {
                "MessageSid": "SM123",
                "MessageStatus": "undelivered",
                "ErrorCode": "63016",
                "ErrorMessage": "outside allowed window",
                "access_token": "should-not-be-returned",
                "refresh_token": "should-not-be-returned",
            }
        )

        response = asyncio.run(twilio_status_callback(request))

        self.assertEqual(
            response,
            {
                "updated": True,
                "message_found": True,
                "status": "undelivered",
                "error_code": "63016",
            },
        )
        self.assertNotIn("access_token", response)
        self.assertNotIn("refresh_token", response)
        self.assertNotIn("to_number", response)
        self.assertNotIn("ErrorMessage", response)

        with database.get_session() as session:
            row = session.query(SentMessage).one()

        self.assertEqual(row.status, "undelivered")
        self.assertEqual(row.error_code, "63016")
        self.assertEqual(row.error_message, "outside allowed window")

    def test_twilio_status_callback_missing_sid_returns_safe_error(self):
        response = asyncio.run(twilio_status_callback(FakeRequest({})))

        self.assertEqual(
            response,
            {
                "updated": False,
                "message_found": False,
                "error": "missing_message_sid",
            },
        )
        self.assertNotIn("access_token", response)
        self.assertNotIn("refresh_token", response)
        self.assertNotIn("to_number", response)


if __name__ == "__main__":
    unittest.main()
