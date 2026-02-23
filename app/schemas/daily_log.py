from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class DailyLogCreate(BaseModel):
    log_date: date
    work_hours: float = Field(ge=0, le=24, default=0)
    deep_work_hours: float = Field(ge=0, le=24, default=0)
    tasks_completed: int = Field(ge=0, default=0)
    tasks_planned: int = Field(ge=0, default=0)
    interruptions: int = Field(ge=0, default=0)
    focus_score: int = Field(ge=1, le=10, default=5)
    energy_score: int = Field(ge=1, le=10, default=5)
    stress_level: int = Field(ge=1, le=10, default=5)
    mood: str = "neutral"
    sleep_hours: float = Field(ge=0, le=24, default=7.0)
    exercise_minutes: int = Field(ge=0, default=0)
    social_interaction: int = Field(ge=1, le=10, default=5)
    notes: Optional[str] = None
    highlights: Optional[str] = None
    time_to_complete_seconds: Optional[int] = None


class DailyLogUpdate(BaseModel):
    work_hours: Optional[float] = None
    deep_work_hours: Optional[float] = None
    tasks_completed: Optional[int] = None
    tasks_planned: Optional[int] = None
    interruptions: Optional[int] = None
    focus_score: Optional[int] = None
    energy_score: Optional[int] = None
    stress_level: Optional[int] = None
    mood: Optional[str] = None
    sleep_hours: Optional[float] = None
    exercise_minutes: Optional[int] = None
    social_interaction: Optional[int] = None
    notes: Optional[str] = None
    highlights: Optional[str] = None


class DailyLogResponse(BaseModel):
    id: str
    user_id: str
    log_date: date
    work_hours: float
    deep_work_hours: float
    tasks_completed: int
    tasks_planned: int
    interruptions: int
    focus_score: int
    energy_score: int
    stress_level: int
    mood: str
    sleep_hours: float
    exercise_minutes: int
    social_interaction: int
    productivity_score: Optional[float] = None
    energy_index: Optional[float] = None
    consistency_score: Optional[float] = None
    notes: Optional[str] = None
    highlights: Optional[str] = None
    completed_at: datetime

    class Config:
        from_attributes = True


class DailyLogSummary(BaseModel):
    total_logs: int
    avg_productivity: float
    avg_energy: float
    avg_focus: float
    avg_stress: float
    avg_sleep: float
    current_streak: int
    longest_streak: int
