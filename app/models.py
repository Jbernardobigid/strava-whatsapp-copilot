from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint(
            "strava_object_id",
            "object_type",
            "aspect_type",
            name="uq_processed_events_strava_event",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    strava_object_id = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False)
    aspect_type = Column(String, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default="processed")
    error_message = Column(Text, nullable=True)
