from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class AppUser(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Default user")
    whatsapp_number = Column(String, nullable=True)
    strava_athlete_id = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    strava_tokens = relationship("StravaToken", back_populates="user")
    processed_events = relationship("ProcessedEvent", back_populates="user")


class StravaToken(Base):
    __tablename__ = "strava_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_strava_tokens_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=False, index=True)
    athlete_id = Column(String, nullable=True, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("AppUser", back_populates="strava_tokens")


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
    user_id = Column(Integer, ForeignKey("app_users.id"), nullable=True, index=True)
    strava_object_id = Column(String, nullable=False, index=True)
    object_type = Column(String, nullable=False)
    aspect_type = Column(String, nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default="processed")
    error_message = Column(Text, nullable=True)

    user = relationship("AppUser", back_populates="processed_events")
