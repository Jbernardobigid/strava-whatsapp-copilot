from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
def home():
    return {"message": "Strava WhatsApp Copilot is running"}


@router.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})