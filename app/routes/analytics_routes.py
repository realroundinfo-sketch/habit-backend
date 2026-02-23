from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta

from app.database import get_db
from app.models.user import User
from app.models.burnout_score import BurnoutScore
from app.models.insight import Insight
from app.schemas.analytics import DashboardOverview, AnalyticsData
from app.schemas.burnout import BurnoutScoreResponse, BurnoutSummary
from app.schemas.insight import InsightResponse, InsightUpdate
from app.auth.security import get_current_user
from app.services.analytics import get_dashboard_overview, get_analytics_data
from app.services.burnout import calculate_burnout_risk

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardOverview)
async def dashboard_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_dashboard_overview(db, user.id)
    return DashboardOverview(**data)


@router.get("/data", response_model=AnalyticsData)
async def analytics_data(
    days: int = Query(default=30, ge=7, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_analytics_data(db, user.id, days)
    return AnalyticsData(**data)


@router.get("/burnout", response_model=BurnoutSummary)
async def burnout_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get latest burnout data
    today = date.today()
    current_risk = await calculate_burnout_risk(db, user.id, today)

    # Get burnout history
    start_date = today - timedelta(days=30)
    result = await db.execute(
        select(BurnoutScore)
        .where(BurnoutScore.user_id == user.id)
        .where(BurnoutScore.score_date >= start_date)
        .order_by(BurnoutScore.score_date.desc())
    )
    history = result.scalars().all()

    return BurnoutSummary(
        current_risk_score=current_risk["risk_score"],
        risk_category=current_risk["risk_category"],
        trend_direction=current_risk["trend_direction"],
        trend_change=current_risk["trend_change"],
        risk_factors=current_risk["risk_factors"],
        recommendations=current_risk["recommendations"],
        history=[BurnoutScoreResponse.model_validate(h) for h in history],
    )


@router.get("/insights", response_model=list[InsightResponse])
async def get_insights(
    unread_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Insight)
        .where(Insight.user_id == user.id)
        .where(Insight.is_dismissed == False)
    )
    if unread_only:
        query = query.where(Insight.is_read == False)

    query = query.order_by(Insight.created_at.desc()).limit(limit)
    result = await db.execute(query)
    insights = result.scalars().all()
    return [InsightResponse.model_validate(i) for i in insights]


@router.put("/insights/{insight_id}", response_model=InsightResponse)
async def update_insight(
    insight_id: str,
    data: InsightUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Insight)
        .where(Insight.id == insight_id)
        .where(Insight.user_id == user.id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Insight not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(insight, key, value)

    await db.flush()
    await db.refresh(insight)
    return InsightResponse.model_validate(insight)


@router.post("/insights/mark-all-read")
async def mark_all_insights_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user.id)
        .where(Insight.is_read == False)
    )
    insights = result.scalars().all()
    for insight in insights:
        insight.is_read = True
    await db.flush()
    return {"message": f"Marked {len(insights)} insights as read"}
