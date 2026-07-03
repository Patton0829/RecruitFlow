from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Application, Candidate
from ..schemas import (
    ApplicationUpdate,
    CandidateApplicationOut,
    ConfirmCandidateRequest,
    ConfirmCandidateResponse,
)
from ..services.candidate_matcher import find_existing_candidate
from ..services.tencent_docs_client import TencentDocsClient


router = APIRouter()


@router.post("/candidates/confirm", response_model=ConfirmCandidateResponse)
def confirm_candidate(payload: ConfirmCandidateRequest, db: Session = Depends(get_db)):
    candidate_input = payload.candidate
    application_input = payload.application
    existing, match_type = find_existing_candidate(db, candidate_input)
    matched_existing = existing is not None

    if existing:
        candidate = existing
        _update_candidate(candidate, candidate_input.model_dump())
    else:
        candidate = Candidate()
        _update_candidate(candidate, candidate_input.model_dump())
        db.add(candidate)
        db.flush()

    application = Application(candidate_id=candidate.id, **application_input.model_dump())
    db.add(application)
    db.flush()

    synced = False
    try:
        client = TencentDocsClient()
        application.tencent_record_id = client.add_or_update_application(candidate, application)
        application.last_synced_at = datetime.now()
        synced = True
    except Exception as exc:
        print(f"[TencentDocsClient] sync failed: {exc}")

    db.commit()
    db.refresh(candidate)
    db.refresh(application)

    return ConfirmCandidateResponse(
        success=True,
        candidate_id=candidate.id,
        application_id=application.id,
        matched_existing=matched_existing,
        match_type=match_type,
        synced_to_tencent_docs=synced,
    )


@router.get("/candidates", response_model=list[CandidateApplicationOut])
def list_candidates(
    stage: str | None = None,
    status: str | None = None,
    position: str | None = None,
    source: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Application).options(joinedload(Application.candidate)).join(Application.candidate)
    if stage:
        stmt = stmt.where(Application.stage == stage)
    if status:
        stmt = stmt.where(Application.status == status)
    if position:
        stmt = stmt.where(Application.position.ilike(f"%{position}%"))
    if source:
        stmt = stmt.where(Application.source == source)
    if date_from:
        stmt = stmt.where(Application.interview_time >= date_from)
    if date_to:
        stmt = stmt.where(Application.interview_time <= date_to)
    stmt = stmt.order_by(Application.updated_at.desc())
    return [_to_flattened(app) for app in db.scalars(stmt)]


@router.patch("/applications/{application_id}", response_model=CandidateApplicationOut)
def update_application(
    application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)
):
    app = db.scalar(
        select(Application)
        .options(joinedload(Application.candidate))
        .where(Application.id == application_id)
    )
    if not app:
        raise HTTPException(status_code=404, detail="招聘流程记录不存在。")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(app, key, value)

    try:
        client = TencentDocsClient()
        app.tencent_record_id = client.add_or_update_application(app.candidate, app)
        app.last_synced_at = datetime.now()
    except Exception as exc:
        print(f"[TencentDocsClient] sync failed: {exc}")

    db.commit()
    db.refresh(app)
    return _to_flattened(app)


def _update_candidate(candidate: Candidate, values: dict) -> None:
    skills = values.pop("skills", [])
    candidate.skills_json = json.dumps(skills or [], ensure_ascii=False)
    for key, value in values.items():
        setattr(candidate, key, value)


def _skills(candidate: Candidate) -> list[str]:
    if not candidate.skills_json:
        return []
    try:
        value = json.loads(candidate.skills_json)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _to_flattened(app: Application) -> CandidateApplicationOut:
    candidate = app.candidate
    return CandidateApplicationOut(
        candidate_id=candidate.id,
        application_id=app.id,
        name=candidate.name,
        phone=candidate.phone,
        email=candidate.email,
        school=candidate.school,
        degree=candidate.degree,
        major=candidate.major,
        graduation_year=candidate.graduation_year,
        city=candidate.city,
        skills=_skills(candidate),
        resume_summary=candidate.resume_summary,
        project_summary=candidate.project_summary,
        position=app.position,
        source=app.source,
        stage=app.stage,
        status=app.status,
        owner_hr=app.owner_hr,
        interviewer=app.interviewer,
        interview_time=app.interview_time,
        interview_round=app.interview_round,
        next_action=app.next_action,
        hr_decision=app.hr_decision,
        notes=app.notes,
        tencent_record_id=app.tencent_record_id,
        last_synced_at=app.last_synced_at,
        updated_at=app.updated_at,
    )
