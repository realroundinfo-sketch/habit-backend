import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    role: Mapped[str] = mapped_column(String(20), default="user")  # user, admin, premium

    # Onboarding profile
    work_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # remote, office, hybrid
    work_hours_target: Mapped[float | None] = mapped_column(nullable=True, default=8.0)
    sleep_target: Mapped[float | None] = mapped_column(nullable=True, default=7.5)
    primary_goal: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)  # beginner, intermediate, advanced
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Settings
    daily_reminder_time: Mapped[str | None] = mapped_column(String(10), nullable=True, default="21:00")
    weekly_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_checkin: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    daily_logs = relationship("DailyLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    burnout_scores = relationship("BurnoutScore", back_populates="user", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("Streak", back_populates="user", cascade="all, delete-orphan")
