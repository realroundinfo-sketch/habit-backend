"""
Insight Generation System
Auto-generates behavioral insights using rule-based logic.
"""

import statistics
from datetime import date, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.daily_log import DailyLog
from app.models.insight import Insight


async def generate_insights(
    db: AsyncSession, user_id: UUID, target_date: date
) -> list[dict]:
    """Generate insights from recent behavioral data."""
    # Get last 30 days of logs
    start_date = target_date - timedelta(days=30)
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user_id)
        .where(DailyLog.log_date >= start_date)
        .where(DailyLog.log_date <= target_date)
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if len(logs) < 7:
        return []

    insights = []

    # 1. Sleep vs Productivity correlation
    sleep_prod_insight = _analyze_sleep_productivity(logs)
    if sleep_prod_insight:
        insights.append(sleep_prod_insight)

    # 2. Exercise impact
    exercise_insight = _analyze_exercise_impact(logs)
    if exercise_insight:
        insights.append(exercise_insight)

    # 3. Best day of week
    best_day_insight = _analyze_best_day(logs)
    if best_day_insight:
        insights.append(best_day_insight)

    # 4. Energy pattern
    energy_insight = _analyze_energy_patterns(logs)
    if energy_insight:
        insights.append(energy_insight)

    # 5. Stress correlation
    stress_insight = _analyze_stress_impact(logs)
    if stress_insight:
        insights.append(stress_insight)

    # 6. Productivity trend
    trend_insight = _analyze_productivity_trend(logs)
    if trend_insight:
        insights.append(trend_insight)

    # 7. Deep work impact
    deep_work_insight = _analyze_deep_work(logs)
    if deep_work_insight:
        insights.append(deep_work_insight)

    # 8. Consistency insight
    consistency_insight = _analyze_consistency(logs)
    if consistency_insight:
        insights.append(consistency_insight)

    # Save new insights to database
    for insight_data in insights:
        existing = await db.execute(
            select(Insight)
            .where(Insight.user_id == user_id)
            .where(Insight.title == insight_data["title"])
            .where(Insight.created_at >= start_date)
        )
        if existing.scalar_one_or_none() is None:
            insight = Insight(
                user_id=user_id,
                category=insight_data["category"],
                title=insight_data["title"],
                message=insight_data["message"],
                insight_type=insight_data["insight_type"],
                severity=insight_data["severity"],
                impact_score=insight_data.get("impact_score"),
                confidence=insight_data.get("confidence", 0.7),
            )
            db.add(insight)

    await db.flush()
    return insights


def _analyze_sleep_productivity(logs: list) -> Optional[dict]:
    good_sleep_logs = [l for l in logs if l.sleep_hours >= 7]
    poor_sleep_logs = [l for l in logs if l.sleep_hours < 6]

    if len(good_sleep_logs) < 3 or len(poor_sleep_logs) < 2:
        return None

    good_prod = statistics.mean([l.productivity_score or 50 for l in good_sleep_logs])
    poor_prod = statistics.mean([l.productivity_score or 50 for l in poor_sleep_logs])

    diff_pct = ((good_prod - poor_prod) / max(poor_prod, 1)) * 100

    if diff_pct > 10:
        return {
            "category": "sleep",
            "title": "Sleep boosts your productivity",
            "message": f"You perform {diff_pct:.0f}% better after 7+ hours of sleep. "
                       f"On well-rested days, your avg productivity is {good_prod:.0f} vs {poor_prod:.0f} on sleep-deprived days.",
            "insight_type": "observation",
            "severity": "info",
            "impact_score": diff_pct,
            "confidence": min(0.5 + len(logs) / 60, 0.95),
        }
    return None


def _analyze_exercise_impact(logs: list) -> Optional[dict]:
    exercise_logs = [l for l in logs if l.exercise_minutes >= 20]
    no_exercise_logs = [l for l in logs if l.exercise_minutes == 0]

    if len(exercise_logs) < 3 or len(no_exercise_logs) < 3:
        return None

    ex_prod = statistics.mean([l.productivity_score or 50 for l in exercise_logs])
    no_prod = statistics.mean([l.productivity_score or 50 for l in no_exercise_logs])

    diff = ex_prod - no_prod

    if diff > 5:
        return {
            "category": "productivity",
            "title": "Exercise improves your output",
            "message": f"Days with exercise show {diff:.0f} points higher productivity. "
                       f"Exercise also improves your consistency and energy levels.",
            "insight_type": "recommendation",
            "severity": "success",
            "impact_score": diff,
            "confidence": 0.75,
        }
    return None


def _analyze_best_day(logs: list) -> Optional[dict]:
    day_scores: dict[str, list] = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for log in logs:
        day_name = day_names[log.log_date.weekday()]
        if log.productivity_score is not None:
            day_scores.setdefault(day_name, []).append(log.productivity_score)

    if len(day_scores) < 3:
        return None

    day_averages = {d: statistics.mean(s) for d, s in day_scores.items() if len(s) >= 2}
    if not day_averages:
        return None

    best_day = max(day_averages, key=day_averages.get)
    worst_day = min(day_averages, key=day_averages.get)

    if day_averages[best_day] - day_averages[worst_day] > 8:
        return {
            "category": "productivity",
            "title": f"{best_day} is your peak day",
            "message": f"Your highest productivity occurs on {best_day}s (avg: {day_averages[best_day]:.0f}). "
                       f"Consider scheduling important work on {best_day}s. "
                       f"{worst_day}s tend to be lower ({day_averages[worst_day]:.0f}).",
            "insight_type": "observation",
            "severity": "info",
            "impact_score": day_averages[best_day] - day_averages[worst_day],
            "confidence": 0.7,
        }
    return None


def _analyze_energy_patterns(logs: list) -> Optional[dict]:
    recent = logs[-7:]
    if len(recent) < 5:
        return None

    avg_energy = statistics.mean([l.energy_score for l in recent])
    energy_trend = [l.energy_score for l in recent]

    # Check if energy is declining
    first_half = energy_trend[:len(energy_trend)//2]
    second_half = energy_trend[len(energy_trend)//2:]

    if statistics.mean(second_half) < statistics.mean(first_half) - 1:
        return {
            "category": "energy",
            "title": "Energy levels declining",
            "message": f"Your energy has been dropping this week (avg: {avg_energy:.1f}/10). "
                       "Consider: better sleep, more breaks, or lighter workload.",
            "insight_type": "alert",
            "severity": "warning",
            "impact_score": statistics.mean(first_half) - statistics.mean(second_half),
            "confidence": 0.7,
        }
    return None


def _analyze_stress_impact(logs: list) -> Optional[dict]:
    high_stress = [l for l in logs if l.stress_level >= 7]
    low_stress = [l for l in logs if l.stress_level <= 4]

    if len(high_stress) < 3 or len(low_stress) < 3:
        return None

    high_prod = statistics.mean([l.productivity_score or 50 for l in high_stress])
    low_prod = statistics.mean([l.productivity_score or 50 for l in low_stress])

    if low_prod > high_prod + 8:
        return {
            "category": "productivity",
            "title": "Stress is hurting your output",
            "message": f"High-stress days show {low_prod - high_prod:.0f} points lower productivity. "
                       "Managing stress could significantly boost your performance.",
            "insight_type": "recommendation",
            "severity": "warning",
            "impact_score": low_prod - high_prod,
            "confidence": 0.75,
        }
    return None


def _analyze_productivity_trend(logs: list) -> Optional[dict]:
    if len(logs) < 14:
        return None

    recent_7 = logs[-7:]
    previous_7 = logs[-14:-7]

    recent_avg = statistics.mean([l.productivity_score or 50 for l in recent_7])
    prev_avg = statistics.mean([l.productivity_score or 50 for l in previous_7])

    change = recent_avg - prev_avg

    if change > 5:
        return {
            "category": "productivity",
            "title": "Productivity improving",
            "message": f"Your productivity increased by {change:.0f} points this week compared to last week. "
                       "Keep up the great work!",
            "insight_type": "achievement",
            "severity": "success",
            "impact_score": change,
            "confidence": 0.8,
        }
    elif change < -8:
        return {
            "category": "productivity",
            "title": "Productivity dip detected",
            "message": f"Your productivity dropped by {abs(change):.0f} points compared to last week. "
                       "Review your recent habits and energy levels for clues.",
            "insight_type": "alert",
            "severity": "warning",
            "impact_score": abs(change),
            "confidence": 0.8,
        }
    return None


def _analyze_deep_work(logs: list) -> Optional[dict]:
    high_dw = [l for l in logs if l.deep_work_hours >= 3]
    low_dw = [l for l in logs if l.deep_work_hours < 1.5]

    if len(high_dw) < 3 or len(low_dw) < 3:
        return None

    high_prod = statistics.mean([l.productivity_score or 50 for l in high_dw])
    low_prod = statistics.mean([l.productivity_score or 50 for l in low_dw])

    if high_prod > low_prod + 10:
        return {
            "category": "productivity",
            "title": "Deep work drives results",
            "message": f"Days with 3+ hours of deep work show {high_prod - low_prod:.0f} points higher productivity. "
                       "Protect your deep work time blocks.",
            "insight_type": "observation",
            "severity": "info",
            "impact_score": high_prod - low_prod,
            "confidence": 0.8,
        }
    return None


def _analyze_consistency(logs: list) -> Optional[dict]:
    if len(logs) < 14:
        return None

    scores = [l.productivity_score or 50 for l in logs[-14:]]
    recent_std = statistics.stdev(scores[-7:]) if len(scores) >= 7 else 0
    prev_std = statistics.stdev(scores[:7]) if len(scores) >= 14 else 0

    if prev_std > 0 and recent_std < prev_std * 0.7:
        return {
            "category": "productivity",
            "title": "Your consistency is improving",
            "message": "Your daily performance variance has decreased. "
                       "A consistent routine is one of the strongest predictors of long-term success.",
            "insight_type": "achievement",
            "severity": "success",
            "confidence": 0.7,
        }
    return None
