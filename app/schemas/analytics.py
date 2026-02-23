from pydantic import BaseModel
from typing import Optional


class DashboardOverview(BaseModel):
    # Today's scores
    today_productivity: Optional[float] = None
    today_energy: Optional[float] = None
    today_focus: Optional[int] = None
    today_stress: Optional[int] = None
    has_checked_in_today: bool = False

    # Streaks
    checkin_streak: int = 0
    longest_checkin_streak: int = 0

    # Weekly averages
    weekly_avg_productivity: float = 0.0
    weekly_avg_energy: float = 0.0
    weekly_avg_focus: float = 0.0
    weekly_avg_stress: float = 0.0

    # Monthly trend
    monthly_productivity_trend: float = 0.0  # percentage change
    monthly_energy_trend: float = 0.0

    # Burnout
    burnout_risk_score: float = 0.0
    burnout_risk_category: str = "low"

    # Goals & Habits
    active_goals: int = 0
    completed_goals: int = 0
    active_habits: int = 0
    habits_completed_today: int = 0
    habits_total_today: int = 0

    # Consistency
    consistency_score: float = 0.0

    # Unread insights
    unread_insights: int = 0


class WeeklyReport(BaseModel):
    week_start: str
    week_end: str
    avg_productivity: float
    avg_energy: float
    avg_focus: float
    avg_stress: float
    avg_sleep: float
    total_deep_work_hours: float
    total_tasks_completed: int
    checkin_days: int
    habits_completion_rate: float
    goals_progress: list[dict]
    burnout_trend: list[dict]
    top_insights: list[str]
    productivity_by_day: list[dict]
    energy_by_day: list[dict]


class AnalyticsData(BaseModel):
    # Time series
    productivity_trend: list[dict]
    energy_trend: list[dict]
    focus_trend: list[dict]
    stress_trend: list[dict]
    sleep_trend: list[dict]

    # Correlations
    sleep_productivity_correlation: float = 0.0
    exercise_productivity_correlation: float = 0.0
    energy_focus_correlation: float = 0.0

    # Patterns
    best_day_of_week: Optional[str] = None
    peak_productivity_time: Optional[str] = None
    performance_volatility: float = 0.0

    # Distributions
    mood_distribution: dict = {}
    productivity_distribution: dict = {}
