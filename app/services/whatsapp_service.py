from twilio.rest import Client

from app.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER,
    YOUR_WHATSAPP_NUMBER,
)
from app.utils.logger import get_logger
from app.utils.storage import mask_whatsapp_number, record_sent_message

logger = get_logger(__name__)


def send_whatsapp_message(body: str) -> str:
    missing = []
    if not TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not TWILIO_WHATSAPP_NUMBER:
        missing.append("TWILIO_WHATSAPP_NUMBER")
    if not YOUR_WHATSAPP_NUMBER:
        missing.append("YOUR_WHATSAPP_NUMBER")

    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    message = client.messages.create(
        body=body,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=YOUR_WHATSAPP_NUMBER,
    )
    initial_status = getattr(message, "status", None) or "accepted"

    record_sent_message(
        twilio_message_sid=message.sid,
        to_number=YOUR_WHATSAPP_NUMBER,
        status=initial_status,
    )

    logger.info(
        "WhatsApp message accepted by Twilio: sid=%s to=%s status=%s",
        message.sid,
        mask_whatsapp_number(YOUR_WHATSAPP_NUMBER),
        initial_status,
    )

    return message.sid
