"""
Productivity Scoring Engine
Converts raw daily data → scores → insights → recommendations.
"""

import statistics
from typing import Optional
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.models.daily_log import DailyLog


def calculate_productivity_score(log: DailyLog) -> float:
    """
    Productivity Score =
    (Deep Work × 0.35) + (Focus Score × 0.25) + (Task Completion × 0.15)
    + (Energy Score × 0.15) + (Low Distraction Bonus × 0.10)

    Normalized to 0-100.
    """
    # Normalize deep work (0-8 hours → 0-100)
    deep_work_normalized = min(log.deep_work_hours / 8.0, 1.0) * 100

    # Focus score already 1-10, normalize to 0-100
    focus_normalized = (log.focus_score / 10.0) * 100

    # Task completion ratio
    if log.tasks_planned > 0:
        task_ratio = min(log.tasks_completed / log.tasks_planned, 1.5)
    else:
        task_ratio = 0.5 if log.tasks_completed > 0 else 0.0
    task_normalized = min(task_ratio * 100, 100)

    # Energy score 1-10 → 0-100
    energy_normalized = (log.energy_score / 10.0) * 100

    # Low distraction bonus (fewer interruptions = higher score)
    if log.interruptions <= 2:
        distraction_bonus = 100
    elif log.interruptions <= 5:
        distraction_bonus = 75
    elif log.interruptions <= 10:
        distraction_bonus = 50
    elif log.interruptions <= 15:
        distraction_bonus = 25
    else:
        distraction_bonus = 10

    score = (
        deep_work_normalized * 0.35
        + focus_normalized * 0.25
        + task_normalized * 0.15
        + energy_normalized * 0.15
        + distraction_bonus * 0.10
    )

    return round(min(max(score, 0), 100), 1)


def calculate_energy_index(log: DailyLog) -> float:
    """Calculate energy index from multiple signals."""
    energy_base = (log.energy_score / 10.0) * 100
    sleep_factor = min(log.sleep_hours / 8.0, 1.0) * 100
    stress_penalty = ((10 - log.stress_level) / 10.0) * 100
    exercise_bonus = min(log.exercise_minutes / 60.0, 1.0) * 20

    index = (
        energy_base * 0.40
        + sleep_factor * 0.30
        + stress_penalty * 0.20
        + exercise_bonus * 0.10
    )

    return round(min(max(index, 0), 100), 1)


async def calculate_consistency_score(
    db: AsyncSession, user_id: UUID, target_date: date, window: int = 7
) -> float:
    """
    Consistency Index = Standard Deviation Reduction Across 7 Days
    Lower variance = higher consistency.
    """
    start_date = target_date - timedelta(days=window)
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= start_date)
        .where(DailyLog.log_date <= target_date)
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if len(logs) < 3:
        return 50.0  # Not enough data

    # Calculate consistency from multiple dimensions
    scores = []
    sleep_times = []
    work_times = []

    for log in logs:
        if log.productivity_score is not None:
            scores.append(log.productivity_score)
        sleep_times.append(log.sleep_hours)
        work_times.append(log.work_hours)

    consistency_factors = []

    if len(scores) >= 3:
        score_std = statistics.stdev(scores)
        # Lower std = more consistent. Max expected std ~30
        score_consistency = max(0, 100 - (score_std / 30.0 * 100))
        consistency_factors.append(score_consistency)

    if len(sleep_times) >= 3:
        sleep_std = statistics.stdev(sleep_times)
        sleep_consistency = max(0, 100 - (sleep_std / 3.0 * 100))
        consistency_factors.append(sleep_consistency)

    if len(work_times) >= 3:
        work_std = statistics.stdev(work_times)
        work_consistency = max(0, 100 - (work_std / 4.0 * 100))
        consistency_factors.append(work_consistency)

    # Streak bonus: more days logged = more consistent
    streak_bonus = min(len(logs) / window, 1.0) * 20

    if consistency_factors:
        base_score = statistics.mean(consistency_factors)
        return round(min(max(base_score + streak_bonus, 0), 100), 1)

    return 50.0
