from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.habit import Habit, HabitLog
from app.models.event import Event
from app.schemas.habit import (
    HabitCreate, HabitUpdate, HabitLogCreate,
    HabitResponse, HabitLogResponse, HabitWithLogs,
)
from app.auth.security import get_current_user

router = APIRouter(prefix="/habits", tags=["Habits"])


@router.get("/", response_model=list[HabitWithLogs])
async def get_habits(
    include_archived: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Habit).where(Habit.user_id == user.id)
    if not include_archived:
        query = query.where(Habit.is_archived == False)
    query = query.order_by(Habit.created_at.desc())

    result = await db.execute(query)
    habits = result.scalars().all()

    today = date.today()
    response = []
    for habit in habits:
        logs_result = await db.execute(
            select(HabitLog)
            .where(HabitLog.habit_id == habit.id)
            .where(HabitLog.log_date >= today - timedelta(days=30))
            .order_by(HabitLog.log_date.desc())
        )
        recent_logs = logs_result.scalars().all()

        today_log = next((l for l in recent_logs if l.log_date == today), None)
        today_completed = today_log.completed if today_log else False
        today_progress = today_log.progress_value if today_log else 0.0

        habit_data = HabitWithLogs(
            **{c.name: getattr(habit, c.name) for c in habit.__table__.columns},
            recent_logs=[HabitLogResponse.model_validate(l) for l in recent_logs],
            today_completed=today_completed,
            today_progress=today_progress,
        )
        response.append(habit_data)

    return response


@router.post("/", response_model=HabitResponse, status_code=201)
async def create_habit(
    data: HabitCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = Habit(user_id=user.id, **data.model_dump())
    db.add(habit)

    event = Event(
        user_id=user.id,
        event_type="habit_created",
        event_category="habit",
        event_data=f'{{"habit_name": "{data.name}", "category": "{data.category}", "target_type": "{data.target_type}"}}',
    )
    db.add(event)

    await db.flush()
    await db.refresh(habit)
    return HabitResponse.model_validate(habit)


@router.put("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: str,
    data: HabitUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Habit)
        .where(Habit.id == habit_id)
        .where(Habit.user_id == user.id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(habit, key, value)

    habit.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(habit)
    return HabitResponse.model_validate(habit)


@router.delete("/{habit_id}", status_code=204)
async def delete_habit(
    habit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Habit)
        .where(Habit.id == habit_id)
        .where(Habit.user_id == user.id)
    )
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    await db.delete(habit)
    await db.flush()


@router.post("/log", response_model=HabitLogResponse, status_code=201)
async def log_habit(
    data: HabitLogCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify habit belongs to user
    habit_result = await db.execute(
        select(Habit)
        .where(Habit.id == data.habit_id)
        .where(Habit.user_id == user.id)
    )
    habit = habit_result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    # Auto-determine completed status based on target
    completed = data.completed
    if habit.target_type == "binary":
        completed = data.completed
    elif habit.target_type in ("quantity", "time"):
        # Auto-complete when progress meets or exceeds target
        completed = data.progress_value >= habit.target_value

    # Check for existing log on this date
    existing = await db.execute(
        select(HabitLog)
        .where(HabitLog.habit_id == data.habit_id)
        .where(HabitLog.log_date == data.log_date)
    )
    existing_log = existing.scalar_one_or_none()
    if existing_log:
        existing_log.completed = completed
        existing_log.progress_value = data.progress_value
        existing_log.notes = data.notes
        existing_log.completed_at = datetime.utcnow()
        await db.flush()
        await db.refresh(existing_log)
        log = existing_log
    else:
        log = HabitLog(
            user_id=user.id,
            habit_id=data.habit_id,
            log_date=data.log_date,
            completed=completed,
            progress_value=data.progress_value,
            notes=data.notes,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)

    # Update habit stats
    await _update_habit_stats(db, habit, data.log_date)

    event = Event(
        user_id=user.id,
        event_type="habit_logged",
        event_category="habit",
        event_data=f'{{"habit_id": "{habit.id}", "completed": {str(completed).lower()}, "progress": {data.progress_value}}}',
    )
    db.add(event)
    await db.flush()

    return HabitLogResponse.model_validate(log)


@router.get("/{habit_id}/logs", response_model=list[HabitLogResponse])
async def get_habit_logs(
    habit_id: str,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)
    result = await db.execute(
        select(HabitLog)
        .where(HabitLog.habit_id == habit_id)
        .where(HabitLog.user_id == user.id)
        .where(HabitLog.log_date >= start_date)
        .order_by(HabitLog.log_date.desc())
    )
    logs = result.scalars().all()
    return [HabitLogResponse.model_validate(l) for l in logs]


async def _update_habit_stats(db: AsyncSession, habit: Habit, log_date: date):
    """Update habit statistics after logging."""
    result = await db.execute(
        select(HabitLog)
        .where(HabitLog.habit_id == habit.id)
        .where(HabitLog.completed == True)
        .order_by(HabitLog.log_date.desc())
    )
    completed_logs = result.scalars().all()

    habit.total_completions = len(completed_logs)

    # Success rate (last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_logs = [l for l in completed_logs if l.log_date >= thirty_days_ago]
    expected_days = min(habit.target_days_per_week * 4, 30)
    habit.success_rate = round(min(len(recent_logs) / max(expected_days, 1), 1.0) * 100, 1)

    # Streak
    if completed_logs:
        dates = sorted([l.log_date for l in completed_logs], reverse=True)
        streak = 1
        for i in range(1, len(dates)):
            if (dates[i - 1] - dates[i]).days <= 2:
                streak += 1
            else:
                break
        habit.current_streak = streak
        habit.longest_streak = max(habit.longest_streak, streak)

    # Health score
    created_date = habit.created_at
    if isinstance(created_date, datetime):
        created_date = created_date.date()
    duration_factor = min((date.today() - created_date).days / 30, 3.0) / 3.0
    consistency_factor = habit.success_rate / 100
    habit.health_score = round(consistency_factor * duration_factor * 100, 1)

    await db.flush()
