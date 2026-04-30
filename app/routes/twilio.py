from fastapi import APIRouter, Request

from app.utils.storage import update_sent_message_status

router = APIRouter()


@router.post("/webhook/twilio/status")
async def twilio_status_callback(request: Request):
    form = await request.form()

    message_sid = form.get("MessageSid")
    status = form.get("MessageStatus") or form.get("SmsStatus")
    error_code = form.get("ErrorCode")
    error_message = form.get("ErrorMessage")

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
