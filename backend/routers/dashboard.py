from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Application, Candidate
from ..schemas import DashboardSummary
from .candidates import _to_flattened


router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today + timedelta(days=1), time.min)
    now = datetime.now()
    two_days_ago = now - timedelta(days=2)

    total_candidates = db.scalar(select(func.count(Candidate.id))) or 0
    active_applications = (
        db.scalar(select(func.count(Application.id)).where(Application.status == "进行中")) or 0
    )
    today_interviews = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.status == "进行中",
                Application.interview_time >= start,
                Application.interview_time < end,
            )
        )
        or 0
    )
    upcoming_1h_interviews = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.status == "进行中",
                Application.interview_time >= now,
                Application.interview_time <= now + timedelta(hours=1),
            )
        )
        or 0
    )
    overdue_followups = (
        db.scalar(
            select(func.count(Application.id)).where(
                Application.status == "进行中",
                Application.updated_at <= two_days_ago,
                Application.stage.not_in(["已入职", "淘汰", "候选人放弃", "进入人才库"]),
            )
        )
        or 0
    )

    stage_counts = {
        stage: count
        for stage, count in db.execute(
            select(Application.stage, func.count(Application.id))
            .group_by(Application.stage)
            .order_by(func.count(Application.id).desc())
        ).all()
    }
    source_counts = {
        source: count
        for source, count in db.execute(
            select(Application.source, func.count(Application.id))
            .group_by(Application.source)
            .order_by(func.count(Application.id).desc())
        ).all()
    }
    today_apps = list(
        db.scalars(
            select(Application)
            .options(joinedload(Application.candidate))
            .where(
                Application.status == "进行中",
                Application.interview_time >= start,
                Application.interview_time < end,
            )
            .order_by(Application.interview_time.asc())
        )
    )

    return DashboardSummary(
        total_candidates=total_candidates,
        active_applications=active_applications,
        today_interviews=today_interviews,
        upcoming_1h_interviews=upcoming_1h_interviews,
        overdue_followups=overdue_followups,
        stage_counts=stage_counts,
        source_counts=source_counts,
        today_interview_list=[_to_flattened(app) for app in today_apps],
    )
