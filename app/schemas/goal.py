from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str  # output, habit, time, learning, health
    metric: str
    target_value: float = Field(gt=0)
    unit: str = "units"
    priority_weight: float = Field(ge=0.1, le=3.0, default=1.0)
    start_date: date
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    current_value: Optional[float] = None
    priority_weight: Optional[float] = None
    status: Optional[str] = None
    deadline: Optional[date] = None


class GoalProgressUpdate(BaseModel):
    value: float  # Value to add to current_value


class GoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    category: str
    metric: str
    target_value: float
    current_value: float
    unit: str
    priority_weight: float
    goal_score: Optional[float] = None
    success_probability: Optional[float] = None
    start_date: date
    deadline: Optional[date] = None
    status: str
    is_active: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_progress(cls, goal):
        progress = min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0
        return cls(
            **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
            progress_percentage=progress,
        )
