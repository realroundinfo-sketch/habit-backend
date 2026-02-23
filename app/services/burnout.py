"""
Burnout Prediction Engine
Rule-based predictive model for burnout risk assessment.
"""

import json
import statistics
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.daily_log import DailyLog
from app.models.habit import Habit, HabitLog
from app.models.burnout_score import BurnoutScore


async def calculate_burnout_risk(
    db: AsyncSession, user_id: UUID, target_date: date
) -> dict:
    """
    Burnout Risk =
    (Workload Trend × 0.25) + (Energy Decline × 0.25) +
    (Sleep Deficit × 0.15) + (Stress Level × 0.15) + (Productivity Drop × 0.20)

    Returns risk assessment with recommendations.
    """
    # Get last 14 days of logs
    start_date = target_date - timedelta(days=14)
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= start_date)
        .where(DailyLog.log_date <= target_date)
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if len(logs) < 5:
        return {
            "risk_score": 0.0,
            "risk_category": "low",
            "workload_trend": 0.0,
            "energy_decline": 0.0,
            "sleep_deficit": 0.0,
            "stress_score": 0.0,
            "productivity_drop": 0.0,
            "trend_direction": "stable",
            "trend_change": 0.0,
            "recommendations": [],
            "risk_factors": [],
        }

    # Split into first half and second half for trend detection
    mid = len(logs) // 2
    first_half = logs[:mid]
    second_half = logs[mid:]

    # 1. Workload Trend (rising work hours + falling productivity = bad)
    first_work_avg = statistics.mean([l.work_hours for l in first_half])
    second_work_avg = statistics.mean([l.work_hours for l in second_half])
    work_increase = max(0, (second_work_avg - first_work_avg) / max(first_work_avg, 1))

    first_prod_avg = statistics.mean([l.productivity_score or 50 for l in first_half])
    second_prod_avg = statistics.mean([l.productivity_score or 50 for l in second_half])
    prod_with_work = work_increase * 50 + max(0, (first_prod_avg - second_prod_avg)) * 0.5
    workload_trend = min(prod_with_work, 100)

    # 2. Energy Decline
    first_energy = statistics.mean([l.energy_score for l in first_half])
    second_energy = statistics.mean([l.energy_score for l in second_half])
    energy_decline_val = max(0, (first_energy - second_energy) / 10.0) * 100
    energy_decline = min(energy_decline_val, 100)

    # 3. Sleep Deficit (compared to recommended 7.5h)
    recent_sleep = statistics.mean([l.sleep_hours for l in second_half])
    sleep_deficit_hours = max(0, 7.5 - recent_sleep)
    sleep_deficit = min((sleep_deficit_hours / 3.0) * 100, 100)

    # 4. Stress Level
    recent_stress = statistics.mean([l.stress_level for l in second_half])
    stress_score = (recent_stress / 10.0) * 100

    # 5. Productivity Drop
    if first_prod_avg > 0:
        prod_drop = max(0, (first_prod_avg - second_prod_avg) / first_prod_avg) * 100
    else:
        prod_drop = 0
    productivity_drop = min(prod_drop, 100)

    # Calculate overall burnout risk
    risk_score = (
        workload_trend * 0.25
        + energy_decline * 0.25
        + sleep_deficit * 0.15
        + stress_score * 0.15
        + productivity_drop * 0.20
    )
    risk_score = round(min(max(risk_score, 0), 100), 1)

    # Determine risk category
    if risk_score >= 75:
        risk_category = "critical"
    elif risk_score >= 50:
        risk_category = "high"
    elif risk_score >= 30:
        risk_category = "medium"
    else:
        risk_category = "low"

    # Get previous score for trend
    prev_result = await db.execute(
        select(BurnoutScore)
        .where(BurnoutScore.user_id == user_id)
        .where(BurnoutScore.score_date < target_date)
        .order_by(BurnoutScore.score_date.desc())
        .limit(1)
    )
    prev_score = prev_result.scalar_one_or_none()

    if prev_score:
        trend_change = risk_score - prev_score.risk_score
        if trend_change > 5:
            trend_direction = "worsening"
        elif trend_change < -5:
            trend_direction = "improving"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "stable"
        trend_change = 0.0

    # Generate risk factors
    risk_factors = []
    if workload_trend > 40:
        risk_factors.append({"factor": "High Workload", "severity": "high", "score": workload_trend})
    if energy_decline > 30:
        risk_factors.append({"factor": "Energy Declining", "severity": "high", "score": energy_decline})
    if sleep_deficit > 40:
        risk_factors.append({"factor": "Sleep Deficit", "severity": "medium", "score": sleep_deficit})
    if stress_score > 60:
        risk_factors.append({"factor": "High Stress", "severity": "high", "score": stress_score})
    if productivity_drop > 30:
        risk_factors.append({"factor": "Productivity Declining", "severity": "medium", "score": productivity_drop})

    # Generate recommendations
    recommendations = _generate_burnout_recommendations(
        workload_trend, energy_decline, sleep_deficit, stress_score,
        productivity_drop, risk_category, recent_sleep, recent_stress
    )

    return {
        "risk_score": risk_score,
        "risk_category": risk_category,
        "workload_trend": round(workload_trend, 1),
        "energy_decline": round(energy_decline, 1),
        "sleep_deficit": round(sleep_deficit, 1),
        "stress_score": round(stress_score, 1),
        "productivity_drop": round(productivity_drop, 1),
        "trend_direction": trend_direction,
        "trend_change": round(trend_change, 1),
        "recommendations": recommendations,
        "risk_factors": risk_factors,
    }


def _generate_burnout_recommendations(
    workload_trend: float, energy_decline: float, sleep_deficit: float,
    stress_score: float, productivity_drop: float, risk_category: str,
    recent_sleep: float, recent_stress: float
) -> list[str]:
    recommendations = []

    if risk_category in ("critical", "high"):
        recommendations.append("Consider taking a recovery day soon — your signals indicate significant fatigue.")

    if workload_trend > 40:
        recommendations.append("Your work hours are increasing while output is declining. Prioritize deep work over long hours.")

    if energy_decline > 30:
        recommendations.append("Your energy levels are dropping. Incorporate more breaks and energy-restoring activities.")

    if sleep_deficit > 40:
        recommendations.append(f"You're averaging {recent_sleep:.1f}h sleep. Aim for 7-8 hours for optimal recovery.")

    if stress_score > 60:
        recommendations.append("Stress levels are elevated. Try stress-reduction techniques: breathing exercises, walks, or meditation.")

    if productivity_drop > 30:
        recommendations.append("Productivity is declining. Consider reducing meeting load and protecting deep work blocks.")

    if not recommendations:
        recommendations.append("Your metrics look healthy. Keep up your current routine!")

    return recommendations
