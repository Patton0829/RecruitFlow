from __future__ import annotations

import csv
import json
from datetime import datetime
from typing import Any

import requests

from ..config import MOCK_TENCENT_DOCS_CSV, TENCENT_DOCS_STATE_JSON, settings
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
    base_url = "https://docs.qq.com"

    def __init__(self) -> None:
        self.real_mode = settings.tencent_docs_configured
        self.csv_path = MOCK_TENCENT_DOCS_CSV
        self.state_path = TENCENT_DOCS_STATE_JSON

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

    def get_document_url(self) -> str | None:
        if not self.real_mode:
            return None
        if settings.tencent_docs_url:
            return settings.tencent_docs_url
        state_url = self._read_state().get("url")
        return str(state_url) if state_url else None

    def _add_or_update_real(self, candidate: Candidate, application: Application) -> str:
        book_id, sheet_id, state = self._ensure_real_sheet()
        rows = state.setdefault("rows", {})
        app_key = str(application.id)

        row_number = self._row_number_from_record_id(application.tencent_record_id)
        if row_number is None and app_key in rows:
            row_number = int(rows[app_key])
        if row_number is None:
            row_number = int(state.get("next_row") or 2)

        row = self._to_row(f"row-{row_number}", candidate, application)
        values = [[row.get(field, "") for field in FIELDNAMES]]
        end_column = self._column_name(len(FIELDNAMES))
        self._update_values(book_id, f"{sheet_id}!A{row_number}:{end_column}{row_number}", values)

        rows[app_key] = row_number
        state["next_row"] = max(int(state.get("next_row") or 2), row_number + 1)
        self._write_state(state)
        return f"row-{row_number}"

    def _update_reminder_status_real(self, application_id: int, fields: dict) -> None:
        book_id, sheet_id, state = self._ensure_real_sheet()
        row_number = state.get("rows", {}).get(str(application_id))
        if not row_number:
            return

        update_fields = dict(fields)
        update_fields["updated_at"] = datetime.now()
        for field, value in update_fields.items():
            if field not in FIELDNAMES:
                continue
            column = self._column_name(FIELDNAMES.index(field) + 1)
            self._update_values(
                book_id,
                f"{sheet_id}!{column}{row_number}:{column}{row_number}",
                [[self._serialize(value)]],
            )

    def _ensure_real_sheet(self) -> tuple[str, str, dict[str, Any]]:
        state = self._read_state()
        book_id = settings.tencent_docs_file_id or state.get("book_id")
        explicit_sheet_id = settings.tencent_docs_sheet_id
        sheet_id = explicit_sheet_id or state.get("sheet_id")

        if not book_id:
            created = self._create_sheet_file()
            book_id = created["ID"]
            state["book_id"] = book_id
            state["url"] = created.get("url", "")
            state["title"] = created.get("title", settings.tencent_docs_title)
        elif settings.tencent_docs_url:
            state["url"] = settings.tencent_docs_url

        if explicit_sheet_id:
            state["sheet_id"] = explicit_sheet_id
        else:
            first_sheet_id = self._first_sheet_id(book_id)
            if sheet_id != first_sheet_id:
                sheet_id = first_sheet_id
                state["sheet_id"] = sheet_id
                state["header_initialized"] = False
                state["rows"] = {}
                state["next_row"] = 2
            elif not sheet_id:
                sheet_id = first_sheet_id
            state["sheet_id"] = sheet_id

        if not state.get("header_initialized"):
            self._write_header(book_id, sheet_id)
            state["header_initialized"] = True
            state["next_row"] = max(int(state.get("next_row") or 2), 2)

        self._write_state(state)
        return book_id, sheet_id, state

    def _create_sheet_file(self) -> dict[str, Any]:
        payload = self._request(
            "POST",
            "/openapi/drive/v2/files",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"type": "sheet", "title": settings.tencent_docs_title[:36]},
        )
        return payload["data"]

    def _create_recruit_sheet(self, book_id: str) -> str | None:
        try:
            payload = self._request(
                "POST",
                f"/openapi/sheetbook/v2/{book_id}:batchUpdate",
                headers={"Content-Type": "application/json"},
                json={
                    "addSheet": {
                        "properties": {
                            "title": "招聘台账",
                            "index": 0,
                            "gridProperties": {
                                "rowCount": 2000,
                                "columnCount": len(FIELDNAMES),
                            },
                        }
                    }
                },
            )
        except Exception as exc:
            print(f"[TencentDocsClient] create sheet tab failed, fallback to first sheet: {exc}")
            return None
        return (
            payload.get("data", {})
            .get("addSheet", {})
            .get("properties", {})
            .get("sheetID")
        )

    def _first_sheet_id(self, book_id: str) -> str:
        payload = self._request("GET", f"/openapi/sheetbook/v2/{book_id}/sheets-info")
        data = payload.get("data", {})
        sheets = data.get("sheetData") or data.get("getSheet") or []
        if not sheets:
            raise RuntimeError("腾讯文档表格没有可写入的工作表。")
        return sheets[0]["sheetID"]

    def _write_header(self, book_id: str, sheet_id: str) -> None:
        end_column = self._column_name(len(FIELDNAMES))
        self._update_values(book_id, f"{sheet_id}!A1:{end_column}1", [FIELDNAMES])

    def _update_values(self, book_id: str, range_name: str, values: list[list[str]]) -> None:
        self._request(
            "PUT",
            f"/openapi/sheetbook/v2/{book_id}/values/{range_name}",
            headers={"Content-Type": "application/json"},
            json={"values": values},
        )

    def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        request_headers = self._auth_headers()
        request_headers.update(headers or {})
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=request_headers,
            timeout=20,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ret", 0) != 0:
            raise RuntimeError(f"腾讯文档 API 调用失败：{payload}")
        return payload

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Access-Token": settings.tencent_docs_access_token,
            "Client-Id": settings.tencent_docs_client_id,
            "Open-Id": settings.tencent_docs_open_id,
        }

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"rows": {}, "next_row": 2}
        try:
            with self.state_path.open("r", encoding="utf-8") as file:
                state = json.load(file)
        except (json.JSONDecodeError, OSError):
            return {"rows": {}, "next_row": 2}
        state.setdefault("rows", {})
        state.setdefault("next_row", 2)
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _row_number_from_record_id(record_id: str | None) -> int | None:
        if not record_id or not record_id.startswith("row-"):
            return None
        try:
            return int(record_id.split("-", 1)[1])
        except ValueError:
            return None

    @staticmethod
    def _column_name(index: int) -> str:
        chars: list[str] = []
        while index:
            index, remainder = divmod(index - 1, 26)
            chars.append(chr(65 + remainder))
        return "".join(reversed(chars))

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
