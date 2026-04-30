from urllib.parse import parse_qs

from fastapi import APIRouter, Request

from app.utils.storage import update_sent_message_status

router = APIRouter()


async def _twilio_callback_payload(request: Request) -> dict:
    raw_body = await request.body()
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else None for key, values in parsed.items()}


@router.post("/webhook/twilio/status")
async def twilio_status_callback(request: Request):
    payload = await _twilio_callback_payload(request)

    message_sid = payload.get("MessageSid")
    status = payload.get("MessageStatus") or payload.get("SmsStatus")
    error_code = payload.get("ErrorCode")
    error_message = payload.get("ErrorMessage")

    if not message_sid:
        return {
            "updated": False,
            "message_found": False,
            "error": "missing_message_sid",
        }

    result = update_sent_message_status(
        twilio_message_sid=message_sid,
        status=status,
        error_code=error_code,
        error_message=error_message,
    )

    return {
        "updated": result["updated"],
        "message_found": result["message_found"],
        "status": result["status"],
        "error_code": result["error_code"],
    }
