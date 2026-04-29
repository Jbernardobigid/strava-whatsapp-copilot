from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from app.models import Base

_engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False)


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


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
