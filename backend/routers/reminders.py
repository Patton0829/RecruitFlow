from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ReminderResponse
from ..services.reminder_service import ReminderService


router = APIRouter()


@router.post("/send-daily-summary", response_model=ReminderResponse)
def send_daily_summary(db: Session = Depends(get_db)):
    return ReminderService().send_daily_summary(db)


@router.post("/scan-upcoming", response_model=ReminderResponse)
def scan_upcoming(db: Session = Depends(get_db)):
    return ReminderService().scan_upcoming_interviews(db)


@router.post("/test-wecom", response_model=ReminderResponse)
def test_wecom():
    return ReminderService().send_test_message()
