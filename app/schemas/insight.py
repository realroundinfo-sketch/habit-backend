from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class InsightResponse(BaseModel):
    id: str
    user_id: str
    category: str
    title: str
    message: str
    insight_type: str
    severity: str
    impact_score: Optional[float] = None
    confidence: float
    is_read: bool
    is_dismissed: bool
    is_actionable: bool
    created_at: datetime

    class Config:
        from_attributes = True


class InsightUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_dismissed: Optional[bool] = None
