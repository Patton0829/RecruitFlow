from __future__ import annotations

from datetime import date, datetime, time, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..database import SessionLocal
from ..models import Application, Candidate
from .tencent_docs_client import TencentDocsClient
from .wecom_bot import WeComBot


TERMINAL_STAGES = {"已入职", "淘汰", "候选人放弃", "进入人才库"}


class ReminderService:
    def __init__(
        self,
        bot: WeComBot | None = None,
        tencent_client: TencentDocsClient | None = None,
    ) -> None:
        self.bot = bot or WeComBot()
        self.tencent_client = tencent_client or TencentDocsClient()

    def send_daily_summary(self, db: Session) -> dict:
        today = date.today()
        start = datetime.combine(today, time.min)
        end = datetime.combine(today + timedelta(days=1), time.min)
        today_str = today.isoformat()

        apps = list(
            db.scalars(
                select(Application)
                .options(joinedload(Application.candidate))
                .where(
                    Application.status == "进行中",
                    Application.interview_time >= start,
                    Application.interview_time < end,
                    or_(
                        Application.daily_summary_sent_date.is_(None),
                        Application.daily_summary_sent_date != today_str,
                    ),
                )
                .order_by(Application.interview_time.asc())
            )
        )

        if not apps:
            total_today = db.scalar(
                select(func.count(Application.id)).where(
                    Application.status == "进行中",
                    Application.interview_time >= start,
                    Application.interview_time < end,
                )
            )
            return {
                "success": True,
                "sent_count": 0,
                "message": "今日面试汇总已发送或今日暂无待发送面试。",
                "logs": [f"今日进行中面试数：{total_today or 0}"],
            }

        lines = ["【今日面试汇总】", "", f"今日共有 {len(apps)} 场面试：", ""]
        for index, app in enumerate(apps, start=1):
            interview_time = app.interview_time.strftime("%H:%M") if app.interview_time else "时间待定"
            candidate_name = app.candidate.name or "候选人"
            round_name = app.interview_round or "面试"
            interviewer = app.interviewer or "待定"
            owner_hr = app.owner_hr or "待定"
            lines.append(
                f"{index}. {candidate_name}｜{app.position}｜{round_name}｜{interview_time}"
                f"｜面试官：{interviewer}｜负责HR：{owner_hr}"
            )
        lines.extend(["", "请提前确认候选人到场情况。"])
        content = self._append_tencent_docs_link("\n".join(lines))

        sent = self.bot.send_markdown(content)
        if not sent:
            return {
                "success": False,
                "sent_count": 0,
                "message": "企业微信消息发送失败。",
                "logs": [content],
            }

        now = datetime.now()
        for app in apps:
            app.daily_summary_sent_date = today_str
            app.last_synced_at = now
            self.tencent_client.add_or_update_application(app.candidate, app)
        db.commit()

        return {
            "success": True,
            "sent_count": len(apps),
            "message": f"已发送今日面试汇总，包含 {len(apps)} 场面试。",
            "logs": [content],
        }

    def scan_upcoming_interviews(self, db: Session) -> dict:
        now = datetime.now()
        window_end = now + timedelta(hours=1)
        apps = list(
            db.scalars(
                select(Application)
                .options(joinedload(Application.candidate))
                .where(
                    Application.status == "进行中",
                    Application.interview_time.is_not(None),
                    Application.interview_time >= now,
                    Application.interview_time <= window_end,
                    Application.reminder_1h_sent_at.is_(None),
                )
                .order_by(Application.interview_time.asc())
            )
        )

        logs: list[str] = []
        sent_count = 0
        for app in apps:
            content = self._build_1h_reminder(app.candidate, app)
            content = self._append_tencent_docs_link(content)
            if self.bot.send_markdown(content):
                app.reminder_1h_sent_at = datetime.now()
                app.last_synced_at = datetime.now()
                self.tencent_client.add_or_update_application(app.candidate, app)
                logs.append(content)
                sent_count += 1

        db.commit()
        return {
            "success": True,
            "sent_count": sent_count,
            "message": f"扫描完成，发送 {sent_count} 条面试前 1 小时提醒。",
            "logs": logs or ["未来 1 小时内暂无待提醒面试。"],
        }

    def send_test_message(self) -> dict:
        content = self._append_tencent_docs_link("【招聘提醒测试】\n> 企业微信群机器人连接正常。")
        ok = self.bot.send_markdown(content)
        return {
            "success": ok,
            "sent_count": 1 if ok else 0,
            "message": "测试消息已发送。" if ok else "测试消息发送失败。",
            "logs": [content],
        }

    def _append_tencent_docs_link(self, content: str) -> str:
        doc_url = self.tencent_client.get_document_url()
        if not doc_url:
            return content
        return f"{content}\n\n腾讯文档台账：[打开查看]({doc_url})"

    @staticmethod
    def _build_1h_reminder(candidate: Candidate, app: Application) -> str:
        interview_time = (
            app.interview_time.strftime("今天 %H:%M") if app.interview_time else "时间待定"
        )
        return "\n".join(
            [
                "【面试前 1 小时提醒】",
                "",
                f"候选人：{candidate.name or '候选人'}",
                f"岗位：{app.position}",
                f"轮次：{app.interview_round or '面试'}",
                f"面试时间：{interview_time}",
                f"面试官：{app.interviewer or '待定'}",
                f"负责 HR：{app.owner_hr or '待定'}",
                "",
                "请提前确认候选人是否收到面试通知。",
            ]
        )


def run_daily_summary_job() -> None:
    db = SessionLocal()
    try:
        ReminderService().send_daily_summary(db)
    finally:
        db.close()


def run_upcoming_scan_job() -> None:
    db = SessionLocal()
    try:
        ReminderService().scan_upcoming_interviews(db)
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.app_timezone)
    scheduler.add_job(
        run_daily_summary_job,
        CronTrigger(
            hour=settings.daily_summary_hour,
            minute=settings.daily_summary_minute,
            timezone=settings.app_timezone,
        ),
        id="daily_interview_summary",
        replace_existing=True,
    )
    scheduler.add_job(
        run_upcoming_scan_job,
        IntervalTrigger(minutes=settings.reminder_scan_interval_minutes),
        id="upcoming_interview_scan",
        replace_existing=True,
    )
    return scheduler
