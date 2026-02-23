from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.daily_log import DailyLog
from app.models.streak import Streak
from app.models.event import Event
from app.schemas.daily_log import DailyLogCreate, DailyLogUpdate, DailyLogResponse, DailyLogSummary
from app.auth.security import get_current_user
from app.services.scoring import (
    calculate_productivity_score,
    calculate_energy_index,
    calculate_consistency_score,
)
from app.services.burnout import calculate_burnout_risk
from app.services.insights import generate_insights
from app.models.burnout_score import BurnoutScore

router = APIRouter(prefix="/checkins", tags=["Daily Check-ins"])


@router.post("/", response_model=DailyLogResponse, status_code=201)
async def create_checkin(
    data: DailyLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for existing log on same date
    existing = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user.id)
        .where(DailyLog.log_date == data.log_date)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Check-in already exists for this date")

    log = DailyLog(user_id=user.id, **data.model_dump())

    # Calculate scores
    log.productivity_score = calculate_productivity_score(log)
    log.energy_index = calculate_energy_index(log)

    db.add(log)
    await db.flush()

    # Calculate consistency (needs DB query)
    log.consistency_score = await calculate_consistency_score(db, user.id, data.log_date)
    await db.flush()

    # Update streak
    await _update_checkin_streak(db, user.id, data.log_date)

    # Update user last checkin
    user.last_checkin = datetime.utcnow()
    await db.flush()

    # Calculate burnout risk (async)
    burnout_data = await calculate_burnout_risk(db, user.id, data.log_date)
    burnout_score = BurnoutScore(
        user_id=user.id,
        score_date=data.log_date,
        risk_score=burnout_data["risk_score"],
        risk_category=burnout_data["risk_category"],
        workload_trend=burnout_data["workload_trend"],
        energy_decline=burnout_data["energy_decline"],
        sleep_deficit=burnout_data["sleep_deficit"],
        stress_score=burnout_data["stress_score"],
        productivity_drop=burnout_data["productivity_drop"],
        trend_direction=burnout_data["trend_direction"],
        trend_change=burnout_data["trend_change"],
        recommendations=str(burnout_data["recommendations"]),
    )
    db.add(burnout_score)

    # Generate insights
    await generate_insights(db, user.id, data.log_date)

    # Track event
    event = Event(
        user_id=user.id,
        event_type="checkin_completed",
        event_category="checkin",
        event_data=f'{{"log_date": "{data.log_date}", "time_to_complete": {data.time_to_complete_seconds or 0}}}',
        duration_seconds=data.time_to_complete_seconds,
    )
    db.add(event)
    await db.flush()

    await db.refresh(log)
    return DailyLogResponse.model_validate(log)


@router.get("/today", response_model=DailyLogResponse | None)
async def get_today_checkin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user.id)
        .where(DailyLog.log_date == date.today())
    )
    log = result.scalar_one_or_none()
    if log:
        return DailyLogResponse.model_validate(log)
    return None


@router.get("/history", response_model=list[DailyLogResponse])
async def get_checkin_history(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user.id)
        .where(DailyLog.log_date >= start_date)
        .order_by(DailyLog.log_date.desc())
    )
    logs = result.scalars().all()
    return [DailyLogResponse.model_validate(l) for l in logs]


@router.get("/summary", response_model=DailyLogSummary)
async def get_checkin_summary(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user.id)
        .where(DailyLog.log_date >= start_date)
        .order_by(DailyLog.log_date)
    )
    logs = result.scalars().all()

    if not logs:
        return DailyLogSummary(
            total_logs=0,
            avg_productivity=0,
            avg_energy=0,
            avg_focus=0,
            avg_stress=0,
            avg_sleep=0,
            current_streak=0,
            longest_streak=0,
        )

    import statistics
    streak_result = await db.execute(
        select(Streak)
        .where(Streak.user_id == user.id)
        .where(Streak.streak_type == "checkin")
    )
    streak = streak_result.scalar_one_or_none()

    return DailyLogSummary(
        total_logs=len(logs),
        avg_productivity=round(statistics.mean([l.productivity_score or 0 for l in logs]), 1),
        avg_energy=round(statistics.mean([l.energy_index or 0 for l in logs]), 1),
        avg_focus=round(statistics.mean([l.focus_score for l in logs]), 1),
        avg_stress=round(statistics.mean([l.stress_level for l in logs]), 1),
        avg_sleep=round(statistics.mean([l.sleep_hours for l in logs]), 1),
        current_streak=streak.current_count if streak else 0,
        longest_streak=streak.longest_count if streak else 0,
    )


@router.put("/{log_date}", response_model=DailyLogResponse)
async def update_checkin(
    log_date: date,
    data: DailyLogUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DailyLog)
        .where(DailyLog.user_id == user.id)
        .where(DailyLog.log_date == log_date)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Check-in not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(log, key, value)

    # Recalculate scores
    log.productivity_score = calculate_productivity_score(log)
    log.energy_index = calculate_energy_index(log)
    log.consistency_score = await calculate_consistency_score(db, user.id, log_date)

    await db.flush()
    await db.refresh(log)
    return DailyLogResponse.model_validate(log)


async def _update_checkin_streak(db: AsyncSession, user_id: str, log_date: date):
    """Update check-in streak for user."""
    result = await db.execute(
        select(Streak)
        .where(Streak.user_id == user_id)
        .where(Streak.streak_type == "checkin")
    )
    streak = result.scalar_one_or_none()

    if not streak:
        streak = Streak(
            user_id=user_id,
            streak_type="checkin",
            current_count=1,
            longest_count=1,
            start_date=log_date,
            last_date=log_date,
            is_active=True,
        )
        db.add(streak)
    else:
        if streak.last_date:
            days_diff = (log_date - streak.last_date).days
            if days_diff == 1:
                streak.current_count += 1
            elif days_diff > 1:
                streak.current_count = 1
                streak.start_date = log_date
            # days_diff == 0 means same day, no change

        streak.last_date = log_date
        if streak.current_count > streak.longest_count:
            streak.longest_count = streak.current_count

    await db.flush()
