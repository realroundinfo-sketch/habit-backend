from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date

from app.database import get_db
from app.models.user import User
from app.models.goal import Goal
from app.models.event import Event
from app.schemas.goal import GoalCreate, GoalUpdate, GoalProgressUpdate, GoalResponse
from app.auth.security import get_current_user

router = APIRouter(prefix="/goals", tags=["Goals"])


@router.get("/", response_model=list[GoalResponse])
async def get_goals(
    status: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Goal).where(Goal.user_id == user.id)
    if status:
        query = query.where(Goal.status == status)
    query = query.order_by(Goal.created_at.desc())

    result = await db.execute(query)
    goals = result.scalars().all()

    response = []
    for goal in goals:
        progress = min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0
        goal_data = GoalResponse(
            **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
            progress_percentage=round(progress, 1),
        )
        response.append(goal_data)

    return response


@router.post("/", response_model=GoalResponse, status_code=201)
async def create_goal(
    data: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    goal = Goal(user_id=user.id, **data.model_dump())

    # Calculate initial goal score
    goal.goal_score = 0.0
    goal.success_probability = _estimate_success_probability(goal)

    db.add(goal)

    event = Event(
        user_id=user.id,
        event_type="goal_created",
        event_category="goal",
        event_data=f'{{"title": "{data.title}", "category": "{data.category}"}}',
    )
    db.add(event)

    await db.flush()
    await db.refresh(goal)

    progress = min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0
    return GoalResponse(
        **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
        progress_percentage=round(progress, 1),
    )


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    data: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .where(Goal.user_id == user.id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(goal, key, value)

    # Check if goal is completed
    if goal.current_value >= goal.target_value and goal.status == "active":
        goal.status = "completed"
        goal.completed_at = datetime.utcnow()

    # Update goal score
    _update_goal_score(goal)
    goal.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(goal)

    progress = min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0
    return GoalResponse(
        **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
        progress_percentage=round(progress, 1),
    )


@router.post("/{goal_id}/progress", response_model=GoalResponse)
async def add_goal_progress(
    goal_id: str,
    data: GoalProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .where(Goal.user_id == user.id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.current_value += data.value

    if goal.current_value >= goal.target_value and goal.status == "active":
        goal.status = "completed"
        goal.completed_at = datetime.utcnow()

        event = Event(
            user_id=user.id,
            event_type="goal_completed",
            event_category="goal",
            event_data=f'{{"goal_id": "{goal.id}", "title": "{goal.title}"}}',
        )
        db.add(event)

    _update_goal_score(goal)
    goal.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(goal)

    progress = min((goal.current_value / goal.target_value) * 100, 100) if goal.target_value > 0 else 0
    return GoalResponse(
        **{c.name: getattr(goal, c.name) for c in goal.__table__.columns},
        progress_percentage=round(progress, 1),
    )


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id)
        .where(Goal.user_id == user.id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    await db.delete(goal)
    await db.flush()


def _update_goal_score(goal: Goal):
    """Goal Score = Progress × Priority × Consistency Factor"""
    if goal.target_value > 0:
        progress = min(goal.current_value / goal.target_value, 1.0)
    else:
        progress = 0.0

    consistency_factor = 1.0
    if goal.deadline and goal.start_date:
        total_days = (goal.deadline - goal.start_date).days
        elapsed_days = (date.today() - goal.start_date).days
        if total_days > 0 and elapsed_days > 0:
            expected_progress = elapsed_days / total_days
            if expected_progress > 0:
                consistency_factor = min(progress / expected_progress, 1.5)

    goal.goal_score = round(progress * goal.priority_weight * consistency_factor * 100, 1)
    goal.success_probability = _estimate_success_probability(goal)


def _estimate_success_probability(goal: Goal) -> float:
    """Estimate probability of goal completion."""
    if goal.status == "completed":
        return 100.0

    if goal.target_value <= 0:
        return 50.0

    progress = goal.current_value / goal.target_value

    if not goal.deadline:
        return round(progress * 80, 1)

    days_remaining = (goal.deadline - date.today()).days
    total_days = (goal.deadline - goal.start_date).days

    if days_remaining <= 0:
        return round(progress * 100, 1)

    if total_days <= 0:
        return 50.0

    time_ratio = days_remaining / total_days
    pace = progress / max(1 - time_ratio, 0.01)

    probability = min(pace * 70 + progress * 30, 99)
    return round(max(probability, 5), 1)
