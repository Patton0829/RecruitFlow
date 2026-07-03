from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


RECRUIT_STAGES = [
    "待筛选",
    "简历通过",
    "待约一面",
    "一面待面",
    "一面通过",
    "待约二面",
    "二面待面",
    "二面通过",
    "Offer待确认",
    "已Offer",
    "已入职",
    "淘汰",
    "候选人放弃",
    "进入人才库",
]

APPLICATION_STATUS = ["进行中", "已通过", "已淘汰", "已放弃", "人才库"]

HR_DECISIONS = ["待决定", "推进下一轮", "暂不推进", "发Offer", "淘汰", "进入人才库"]


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ParsedResume(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    school: str | None = None
    degree: str | None = None
    major: str | None = None
    graduation_year: str | None = None
    city: str | None = None
    skills: list[str] = Field(default_factory=list)
    resume_summary: str | None = None
    project_summary: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("skills", "missing_fields", mode="before")
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class ResumeParseResponse(BaseModel):
    success: bool
    file_path: str
    raw_text_preview: str
    raw_resume_text: str
    parsed: ParsedResume
    parser_mode: str


class CandidateInput(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    school: str | None = None
    degree: str | None = None
    major: str | None = None
    graduation_year: str | None = None
    city: str | None = None
    skills: list[str] = Field(default_factory=list)
    resume_summary: str | None = None
    project_summary: str | None = None
    resume_file_path: str | None = None
    raw_resume_text: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings(cls, value: Any) -> Any:
        return _blank_to_none(value)

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> list[str]:
        return ParsedResume.normalize_list(value)


class ApplicationInput(BaseModel):
    position: str
    source: str
    stage: str = "待筛选"
    status: str = "进行中"
    owner_hr: str
    interviewer: str | None = None
    interview_time: datetime | None = None
    interview_round: str | None = None
    next_action: str | None = None
    hr_decision: str | None = "待决定"
    notes: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings(cls, value: Any) -> Any:
        return _blank_to_none(value)


class ConfirmCandidateRequest(BaseModel):
    candidate: CandidateInput
    application: ApplicationInput


class ConfirmCandidateResponse(BaseModel):
    success: bool
    candidate_id: int
    application_id: int
    matched_existing: bool
    match_type: str | None = None
    synced_to_tencent_docs: bool
    tencent_docs_url: str | None = None


class ApplicationUpdate(BaseModel):
    stage: str | None = None
    status: str | None = None
    interview_time: datetime | None = None
    interviewer: str | None = None
    owner_hr: str | None = None
    interview_round: str | None = None
    next_action: str | None = None
    hr_decision: str | None = None
    notes: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def blank_strings(cls, value: Any) -> Any:
        return _blank_to_none(value)


class CandidateApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    application_id: int
    name: str | None
    phone: str | None
    email: str | None
    school: str | None
    degree: str | None
    major: str | None
    graduation_year: str | None
    city: str | None
    skills: list[str]
    resume_summary: str | None
    project_summary: str | None
    position: str
    source: str
    stage: str
    status: str
    owner_hr: str
    interviewer: str | None
    interview_time: datetime | None
    interview_round: str | None
    next_action: str | None
    hr_decision: str | None
    notes: str | None
    tencent_record_id: str | None
    last_synced_at: datetime | None
    updated_at: datetime


class DashboardSummary(BaseModel):
    total_candidates: int
    active_applications: int
    today_interviews: int
    upcoming_1h_interviews: int
    overdue_followups: int
    stage_counts: dict[str, int]
    source_counts: dict[str, int]
    today_interview_list: list[CandidateApplicationOut] = Field(default_factory=list)


class ReminderResponse(BaseModel):
    success: bool
    sent_count: int = 0
    message: str
    logs: list[str] = Field(default_factory=list)
