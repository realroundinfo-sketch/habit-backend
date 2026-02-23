from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta

from app.database import get_db
from app.models.user import User
from app.models.event import Event
from app.auth.security import get_current_user

router = APIRouter(prefix="/events", tags=["Event Tracking"])


@router.post("/track", status_code=201)
async def track_event(
    event_type: str,
    event_category: str,
    event_data: str = None,
    session_id: str = None,
    duration_seconds: int = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = Event(
        user_id=user.id,
        event_type=event_type,
        event_category=event_category,
        event_data=event_data,
        session_id=session_id,
        duration_seconds=duration_seconds,
    )
    db.add(event)
    await db.flush()
    return {"status": "tracked"}


@router.get("/stats")
async def get_event_stats(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start_date = date.today() - timedelta(days=days)

    # Checkin completion rate
    checkin_count = await db.execute(
        select(func.count(Event.id))
        .where(Event.user_id == user.id)
        .where(Event.event_type == "checkin_completed")
        .where(Event.created_at >= start_date)
    )
    checkins = checkin_count.scalar() or 0

    # Feature usage
    feature_usage = await db.execute(
        select(Event.event_type, func.count(Event.id).label("count"))
        .where(Event.user_id == user.id)
        .where(Event.created_at >= start_date)
        .group_by(Event.event_type)
    )
    usage = {row.event_type: row.count for row in feature_usage}

    # Session time
    session_result = await db.execute(
        select(func.avg(Event.duration_seconds))
        .where(Event.user_id == user.id)
        .where(Event.event_category == "session")
        .where(Event.created_at >= start_date)
    )
    avg_session = session_result.scalar() or 0

    return {
        "checkin_completion_rate": round((checkins / max(days, 1)) * 100, 1),
        "total_checkins": checkins,
        "feature_usage": usage,
        "avg_session_seconds": round(avg_session, 0),
        "period_days": days,
    }
