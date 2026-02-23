from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class BurnoutScoreResponse(BaseModel):
    id: str
    user_id: str
    score_date: date
    risk_score: float
    risk_category: str
    workload_trend: float
    energy_decline: float
    sleep_deficit: float
    stress_score: float
    productivity_drop: float
    trend_direction: str
    trend_change: float
    recommendations: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BurnoutSummary(BaseModel):
    current_risk_score: float
    risk_category: str
    trend_direction: str
    trend_change: float
    risk_factors: list[dict]
    recommendations: list[str]
    history: list[BurnoutScoreResponse]
