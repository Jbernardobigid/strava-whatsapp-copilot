from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.strava import router as strava_router
from app.routes.webhook import router as webhook_router

app = FastAPI(title="Strava WhatsApp Copilot")

app.include_router(health_router)
app.include_router(strava_router)
app.include_router(webhook_router)