from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Candidate
from ..schemas import CandidateInput


def find_existing_candidate(db: Session, candidate: CandidateInput) -> tuple[Candidate | None, str | None]:
    if candidate.phone:
        existing = db.scalar(select(Candidate).where(Candidate.phone == candidate.phone))
        if existing:
            return existing, "phone"

    if candidate.email:
        existing = db.scalar(select(Candidate).where(Candidate.email == candidate.email))
        if existing:
            return existing, "email"

    if candidate.name and candidate.school and candidate.major:
        existing = db.scalar(
            select(Candidate).where(
                Candidate.name == candidate.name,
                Candidate.school == candidate.school,
                Candidate.major == candidate.major,
            )
        )
        if existing:
            return existing, "name_school_major"

    return None, None
