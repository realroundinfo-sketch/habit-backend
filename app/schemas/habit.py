from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class HabitCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "general"
    icon: Optional[str] = None
    color: Optional[str] = None
    # Frequency (rule)
    frequency: str = "daily"  # daily, weekdays, weekly, custom
    target_days_per_week: int = Field(ge=1, le=7, default=7)
    custom_days: Optional[str] = None  # "mon,wed,fri"
    # Target / Progress definition
    target_type: str = "binary"  # binary, quantity, time
    target_value: float = Field(ge=0, default=1.0)
    target_unit: str = ""  # glasses, pages, minutes, etc.
    # Optional
    reminder_time: Optional[str] = None
    difficulty: int = Field(ge=1, le=5, default=3)


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    frequency: Optional[str] = None
    target_days_per_week: Optional[int] = None
    custom_days: Optional[str] = None
    target_type: Optional[str] = None
    target_value: Optional[float] = None
    target_unit: Optional[str] = None
    reminder_time: Optional[str] = None
    difficulty: Optional[int] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None


class HabitLogCreate(BaseModel):
    habit_id: str
    log_date: date
    completed: bool = False
    progress_value: float = 0.0
    notes: Optional[str] = None


class HabitResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    category: str
    icon: Optional[str] = None
    color: Optional[str] = None
    frequency: str
    target_days_per_week: int
    custom_days: Optional[str] = None
    target_type: str
    target_value: float
    target_unit: str
    reminder_time: Optional[str] = None
    difficulty: int
    success_rate: float
    health_score: float
    current_streak: int
    longest_streak: int
    total_completions: int
    is_active: bool
    is_archived: bool
    created_at: datetime

    class Config:
        from_attributes = True


class HabitLogResponse(BaseModel):
    id: str
    habit_id: str
    log_date: date
    completed: bool
    progress_value: float
    notes: Optional[str] = None
    completed_at: datetime

    class Config:
        from_attributes = True


class HabitWithLogs(HabitResponse):
    recent_logs: list[HabitLogResponse] = []
    today_completed: bool = False
    today_progress: float = 0.0
