from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.models import Base

_engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def is_database_configured() -> bool:
    return bool(DATABASE_URL)


def get_engine():
    global _engine

    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")

        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal.configure(bind=_engine)

    return _engine


def get_session():
    get_engine()
    return SessionLocal()


def _ensure_existing_processed_events_user_id(engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE processed_events ADD COLUMN IF NOT EXISTS user_id INTEGER")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_processed_events_user_id "
                "ON processed_events (user_id)"
            )
        )


def init_db() -> bool:
    if not is_database_configured():
        return False

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_existing_processed_events_user_id(engine)
    return True
