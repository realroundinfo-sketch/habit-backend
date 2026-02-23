import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Integer, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BurnoutScore(Base):
    __tablename__ = "burnout_scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    score_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Burnout metrics
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    risk_category: Mapped[str] = mapped_column(String(20), default="low")  # low, medium, high, critical

    # Component scores
    workload_trend: Mapped[float] = mapped_column(Float, default=0.0)
    energy_decline: Mapped[float] = mapped_column(Float, default=0.0)
    sleep_deficit: Mapped[float] = mapped_column(Float, default=0.0)
    stress_score: Mapped[float] = mapped_column(Float, default=0.0)
    productivity_drop: Mapped[float] = mapped_column(Float, default=0.0)

    # Trend
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable")  # improving, stable, worsening
    trend_change: Mapped[float] = mapped_column(Float, default=0.0)

    # Recommendations
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="burnout_scores")
