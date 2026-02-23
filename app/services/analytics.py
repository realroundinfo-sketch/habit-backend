"""
Work Pattern Analytics Engine
Generates analytics and pattern detection from behavioral data.
"""

import statistics
from datetime import date, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.daily_log import DailyLog
from app.models.habit import Habit, HabitLog
from app.models.goal import Goal
from app.models.burnout_score import BurnoutScore
from app.models.insight import Insight
from app.models.streak import Streak


async def get_dashboard_overview(db: AsyncSession, user_id: UUID) -> dict:
    """Generate dashboard overview data."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Today's log
    today_result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date == today)
    )
    today_log = today_result.scalar_one_or_none()

    # Weekly logs
    week_result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= week_start)
        .where(DailyLog.log_date <= today)
    )
    week_logs = week_result.scalars().all()

    # Monthly logs for trend
    month_start = today - timedelta(days=30)
    prev_month_start = today - timedelta(days=60)
    month_result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= prev_month_start)
        .where(DailyLog.log_date <= today)
    )
    all_month_logs = month_result.scalars().all()
    current_month = [l for l in all_month_logs if l.log_date >= month_start]
    prev_month = [l for l in all_month_logs if l.log_date < month_start]

    # Checkin streak
    streak_result = await db.execute(
        select(Streak)
        .where(Streak.user_id == user_id)
        .where(Streak.streak_type == "checkin")
    )
    checkin_streak = streak_result.scalar_one_or_none()

    # Burnout score
    burnout_result = await db.execute(
        select(BurnoutScore)
        .where(BurnoutScore.user_id == user_id)
        .order_by(BurnoutScore.score_date.desc())
        .limit(1)
    )
    latest_burnout = burnout_result.scalar_one_or_none()

    # Goals
    goals_result = await db.execute(
        select(func.count(Goal.id))
        .where(Goal.user_id == user_id)
        .where(Goal.is_active == True)
    )
    active_goals = goals_result.scalar() or 0

    completed_goals_result = await db.execute(
        select(func.count(Goal.id))
        .where(Goal.user_id == user_id)
        .where(Goal.status == "completed")
    )
    completed_goals = completed_goals_result.scalar() or 0

    # Habits
    habits_result = await db.execute(
        select(Habit)
        .where(Habit.user_id == user_id)
        .where(Habit.is_active == True)
    )
    active_habits = habits_result.scalars().all()

    # Today's habit completions
    today_habit_logs = await db.execute(
        select(HabitLog)
        .where(HabitLog.user_id == user_id)
        .where(HabitLog.log_date == today)
        .where(HabitLog.completed == True)
    )
    habits_completed_today = len(today_habit_logs.scalars().all())

    # Unread insights
    unread_result = await db.execute(
        select(func.count(Insight.id))
        .where(Insight.user_id == user_id)
        .where(Insight.is_read == False)
        .where(Insight.is_dismissed == False)
    )
    unread_insights = unread_result.scalar() or 0

    # Calculate weekly averages
    weekly_avg_productivity = 0
    weekly_avg_energy = 0
    weekly_avg_focus = 0
    weekly_avg_stress = 0

    if week_logs:
        weekly_avg_productivity = statistics.mean([l.productivity_score or 0 for l in week_logs])
        weekly_avg_energy = statistics.mean([l.energy_index or 0 for l in week_logs])
        weekly_avg_focus = statistics.mean([l.focus_score for l in week_logs])
        weekly_avg_stress = statistics.mean([l.stress_level for l in week_logs])

    # Monthly trends
    monthly_prod_trend = 0.0
    monthly_energy_trend = 0.0
    if current_month and prev_month:
        curr_prod = statistics.mean([l.productivity_score or 50 for l in current_month])
        prev_prod = statistics.mean([l.productivity_score or 50 for l in prev_month])
        if prev_prod > 0:
            monthly_prod_trend = ((curr_prod - prev_prod) / prev_prod) * 100

        curr_energy = statistics.mean([l.energy_index or 50 for l in current_month])
        prev_energy = statistics.mean([l.energy_index or 50 for l in prev_month])
        if prev_energy > 0:
            monthly_energy_trend = ((curr_energy - prev_energy) / prev_energy) * 100

    # Consistency score (from latest log)
    consistency = 0.0
    if today_log and today_log.consistency_score:
        consistency = today_log.consistency_score
    elif week_logs:
        recent = week_logs[-1]
        consistency = recent.consistency_score or 0.0

    return {
        "today_productivity": today_log.productivity_score if today_log else None,
        "today_energy": today_log.energy_index if today_log else None,
        "today_focus": today_log.focus_score if today_log else None,
        "today_stress": today_log.stress_level if today_log else None,
        "has_checked_in_today": today_log is not None,
        "checkin_streak": checkin_streak.current_count if checkin_streak else 0,
        "longest_checkin_streak": checkin_streak.longest_count if checkin_streak else 0,
        "weekly_avg_productivity": round(weekly_avg_productivity, 1),
        "weekly_avg_energy": round(weekly_avg_energy, 1),
        "weekly_avg_focus": round(weekly_avg_focus, 1),
        "weekly_avg_stress": round(weekly_avg_stress, 1),
        "monthly_productivity_trend": round(monthly_prod_trend, 1),
        "monthly_energy_trend": round(monthly_energy_trend, 1),
        "burnout_risk_score": latest_burnout.risk_score if latest_burnout else 0.0,
        "burnout_risk_category": latest_burnout.risk_category if latest_burnout else "low",
        "active_goals": active_goals,
        "completed_goals": completed_goals,
        "active_habits": len(active_habits),
        "habits_completed_today": habits_completed_today,
        "habits_total_today": len(active_habits),
        "consistency_score": round(consistency, 1),
        "unread_insights": unread_insights,
    }


async def get_analytics_data(
    db: AsyncSession, user_id: UUID, days: int = 30
) -> dict:
    """Generate comprehensive analytics data."""
    today = date.today()
    start_date = today - timedelta(days=days)

    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= start_date)
        .where(DailyLog.log_date <= today)
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if not logs:
        return {
            "productivity_trend": [],
            "energy_trend": [],
            "focus_trend": [],
            "stress_trend": [],
            "sleep_trend": [],
            "sleep_productivity_correlation": 0.0,
            "exercise_productivity_correlation": 0.0,
            "energy_focus_correlation": 0.0,
            "best_day_of_week": None,
            "peak_productivity_time": None,
            "performance_volatility": 0.0,
            "mood_distribution": {},
            "productivity_distribution": {},
        }

    # Time series
    productivity_trend = [{"date": str(l.log_date), "value": l.productivity_score or 0} for l in logs]
    energy_trend = [{"date": str(l.log_date), "value": l.energy_index or 0} for l in logs]
    focus_trend = [{"date": str(l.log_date), "value": l.focus_score} for l in logs]
    stress_trend = [{"date": str(l.log_date), "value": l.stress_level} for l in logs]
    sleep_trend = [{"date": str(l.log_date), "value": l.sleep_hours} for l in logs]

    # Correlations
    sleep_prod_corr = _calculate_correlation(
        [l.sleep_hours for l in logs],
        [l.productivity_score or 50 for l in logs]
    )
    exercise_prod_corr = _calculate_correlation(
        [l.exercise_minutes for l in logs],
        [l.productivity_score or 50 for l in logs]
    )
    energy_focus_corr = _calculate_correlation(
        [l.energy_score for l in logs],
        [l.focus_score for l in logs]
    )

    # Best day of week
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_scores: dict[str, list] = {}
    for log in logs:
        day = day_names[log.log_date.weekday()]
        day_scores.setdefault(day, []).append(log.productivity_score or 50)

    day_averages = {d: statistics.mean(s) for d, s in day_scores.items() if s}
    best_day = max(day_averages, key=day_averages.get) if day_averages else None

    # Performance volatility
    prod_scores = [l.productivity_score or 50 for l in logs]
    volatility = statistics.stdev(prod_scores) if len(prod_scores) >= 2 else 0.0

    # Mood distribution
    mood_counts: dict[str, int] = {}
    for log in logs:
        mood_counts[log.mood] = mood_counts.get(log.mood, 0) + 1

    # Productivity distribution (buckets)
    prod_dist = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for score in prod_scores:
        if score <= 20:
            prod_dist["0-20"] += 1
        elif score <= 40:
            prod_dist["21-40"] += 1
        elif score <= 60:
            prod_dist["41-60"] += 1
        elif score <= 80:
            prod_dist["61-80"] += 1
        else:
            prod_dist["81-100"] += 1

    return {
        "productivity_trend": productivity_trend,
        "energy_trend": energy_trend,
        "focus_trend": focus_trend,
        "stress_trend": stress_trend,
        "sleep_trend": sleep_trend,
        "sleep_productivity_correlation": round(sleep_prod_corr, 2),
        "exercise_productivity_correlation": round(exercise_prod_corr, 2),
        "energy_focus_correlation": round(energy_focus_corr, 2),
        "best_day_of_week": best_day,
        "peak_productivity_time": "Morning",  # Placeholder - need time-of-day data
        "performance_volatility": round(volatility, 1),
        "mood_distribution": mood_counts,
        "productivity_distribution": prod_dist,
    }


def _calculate_correlation(x: list, y: list) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)

    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

    if denom_x == 0 or denom_y == 0:
        return 0.0

    return numerator / (denom_x * denom_y)
