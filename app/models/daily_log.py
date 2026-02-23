import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DailyLog(Base):
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_user_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Work metrics
    work_hours: Mapped[float] = mapped_column(Float, default=0.0)
    deep_work_hours: Mapped[float] = mapped_column(Float, default=0.0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_planned: Mapped[int] = mapped_column(Integer, default=0)
    interruptions: Mapped[int] = mapped_column(Integer, default=0)

    # Subjective scores (1-10)
    focus_score: Mapped[int] = mapped_column(Integer, default=5)
    energy_score: Mapped[int] = mapped_column(Integer, default=5)
    stress_level: Mapped[int] = mapped_column(Integer, default=5)

    # Mood & wellness
    mood: Mapped[str] = mapped_column(String(20), default="neutral")  # great, good, neutral, bad, terrible
    sleep_hours: Mapped[float] = mapped_column(Float, default=7.0)
    exercise_minutes: Mapped[int] = mapped_column(Integer, default=0)
    social_interaction: Mapped[int] = mapped_column(Integer, default=5)  # 1-10

    # Computed scores (0-100)
    productivity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    highlights: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Metadata
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    time_to_complete_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="daily_logs")
