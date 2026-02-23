import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    # Streak data
    streak_type: Mapped[str] = mapped_column(String(50), nullable=False)  # checkin, habit, productivity
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # habit_id if habit streak
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    longest_count: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="streaks")
