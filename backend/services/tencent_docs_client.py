from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import MOCK_TENCENT_DOCS_CSV, settings
from ..models import Application, Candidate


FIELDNAMES = [
    "candidate_id",
    "application_id",
    "name",
    "phone",
    "email",
    "school",
    "degree",
    "major",
    "position",
    "source",
    "stage",
    "status",
    "owner_hr",
    "interviewer",
    "interview_time",
    "interview_round",
    "next_action",
    "hr_decision",
    "notes",
    "daily_summary_sent_date",
    "reminder_1h_sent_at",
    "updated_at",
]


class TencentDocsClient:
    def __init__(self) -> None:
        self.real_mode = settings.tencent_docs_configured
        self.csv_path = MOCK_TENCENT_DOCS_CSV

    def add_or_update_application(self, candidate: Candidate, application: Application) -> str:
        """
        同步候选人和投递信息。
        如果 application.tencent_record_id 为空，则新增记录。
        如果不为空，则更新记录。
        返回 tencent_record_id 或 mock_record_id。
        """
        if self.real_mode:
            return self._add_or_update_real(candidate, application)

        record_id = application.tencent_record_id or f"mock-{application.id}"
        self._upsert_mock_row(record_id, candidate, application)
        return record_id

    def update_reminder_status(self, application_id: int, fields: dict) -> None:
        """
        同步提醒状态。
        """
        if self.real_mode:
            self._update_reminder_status_real(application_id, fields)
            return

        rows = self._read_rows()
        changed = False
        for row in rows:
            if str(row.get("application_id")) == str(application_id):
                for key, value in fields.items():
                    if key in FIELDNAMES:
                        row[key] = self._serialize(value)
                row["updated_at"] = self._serialize(datetime.now())
                changed = True
        if changed:
            self._write_rows(rows)

    def _add_or_update_real(self, candidate: Candidate, application: Application) -> str:
        # TODO: 接入腾讯文档开放平台授权、表格行新增和更新接口。
        print(
            "[TencentDocsClient] Real mode placeholder. "
            f"candidate_id={candidate.id}, application_id={application.id}"
        )
        return application.tencent_record_id or f"tencent-placeholder-{application.id}"

    def _update_reminder_status_real(self, application_id: int, fields: dict) -> None:
        # TODO: 接入腾讯文档开放平台后，将提醒状态同步到对应记录。
        print(f"[TencentDocsClient] Real mode reminder placeholder. {application_id=} {fields=}")

    def _upsert_mock_row(
        self, record_id: str, candidate: Candidate, application: Application
    ) -> None:
        rows = self._read_rows()
        row = self._to_row(record_id, candidate, application)
        updated = False
        for index, existing in enumerate(rows):
            if str(existing.get("application_id")) == str(application.id):
                rows[index] = row
                updated = True
                break
        if not updated:
            rows.append(row)
        self._write_rows(rows)

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))

    def _write_rows(self, rows: list[dict[str, Any]]) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with self.csv_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in FIELDNAMES})

    def _to_row(self, record_id: str, candidate: Candidate, application: Application) -> dict[str, str]:
        return {
            "candidate_id": self._serialize(candidate.id),
            "application_id": self._serialize(application.id),
            "name": self._serialize(candidate.name),
            "phone": self._serialize(candidate.phone),
            "email": self._serialize(candidate.email),
            "school": self._serialize(candidate.school),
            "degree": self._serialize(candidate.degree),
            "major": self._serialize(candidate.major),
            "position": self._serialize(application.position),
            "source": self._serialize(application.source),
            "stage": self._serialize(application.stage),
            "status": self._serialize(application.status),
            "owner_hr": self._serialize(application.owner_hr),
            "interviewer": self._serialize(application.interviewer),
            "interview_time": self._serialize(application.interview_time),
            "interview_round": self._serialize(application.interview_round),
            "next_action": self._serialize(application.next_action),
            "hr_decision": self._serialize(application.hr_decision),
            "notes": self._serialize(application.notes),
            "daily_summary_sent_date": self._serialize(application.daily_summary_sent_date),
            "reminder_1h_sent_at": self._serialize(application.reminder_1h_sent_at),
            "updated_at": self._serialize(datetime.now()),
        }

    @staticmethod
    def _serialize(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)
