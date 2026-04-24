from twilio.rest import Client

from app.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_NUMBER,
    YOUR_WHATSAPP_NUMBER,
)
from app.utils.logger import get_logger

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

    logger.info(
        "WhatsApp message accepted by Twilio: sid=%s to=%s",
        message.sid,
        YOUR_WHATSAPP_NUMBER,
    )

    return message.sid