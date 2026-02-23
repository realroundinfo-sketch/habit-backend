import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Habit definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Frequency (rule — set once during creation)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")  # daily, weekdays, weekly, custom
    target_days_per_week: Mapped[int] = mapped_column(Integer, default=7)
    custom_days: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "mon,wed,fri"

    # Target / Progress type (set during creation)
    target_type: Mapped[str] = mapped_column(String(20), default="binary")  # binary, quantity, time
    target_value: Mapped[float] = mapped_column(Float, default=1.0)  # e.g., 8 glasses, 30 minutes
    target_unit: Mapped[str] = mapped_column(String(30), default="")  # glasses, pages, minutes, etc.

    # Reminder
    reminder_time: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "08:00"

    # Scoring
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    health_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Streak
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_completions: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    habit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_value: Mapped[float] = mapped_column(Float, default=0.0)  # actual progress (glasses, pages, minutes)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    habit = relationship("Habit", back_populates="logs")
