from fastapi import FastAPI

from app.database import init_db
from app.routes.health import router as health_router
from app.routes.strava import router as strava_router
from app.routes.webhook import router as webhook_router
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Strava WhatsApp Copilot")


@app.on_event("startup")
def startup() -> None:
    if init_db():
        logger.info("Database initialized")
    else:
        logger.info("DATABASE_URL not configured; using local JSON persistence fallback")


app.include_router(health_router)
app.include_router(strava_router)
app.include_router(webhook_router)

logger.info("Strava WhatsApp Copilot app started")