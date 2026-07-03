from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MOCK_TENCENT_DOCS_CSV = DATA_DIR / "tencent_docs_mock.csv"
TENCENT_DOCS_STATE_JSON = DATA_DIR / "tencent_docs_state.json"

load_dotenv(ROOT_DIR / ".env")
load_dotenv(Path.cwd() / ".env", override=False)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Settings:
    llm_api_key: str = os.getenv("LLM_API_KEY") or ""
    llm_base_url: str = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    llm_model: str = os.getenv("LLM_MODEL") or ""

    wecom_webhook_url: str = os.getenv("WECOM_WEBHOOK_URL") or ""

    tencent_docs_client_id: str = (
        os.getenv("TENCENT_DOCS_CLIENT_ID") or os.getenv("TENCENT_DOCS_APP_ID") or ""
    )
    tencent_docs_access_token: str = os.getenv("TENCENT_DOCS_ACCESS_TOKEN") or ""
    tencent_docs_open_id: str = os.getenv("TENCENT_DOCS_OPEN_ID") or ""
    tencent_docs_app_secret: str = os.getenv("TENCENT_DOCS_APP_SECRET") or ""
    tencent_docs_file_id: str = os.getenv("TENCENT_DOCS_FILE_ID") or ""
    tencent_docs_sheet_id: str = os.getenv("TENCENT_DOCS_SHEET_ID") or ""
    tencent_docs_title: str = os.getenv("TENCENT_DOCS_TITLE") or "RecruitFlow AI 候选人台账"

    daily_summary_hour: int = _env_int("DAILY_SUMMARY_HOUR", 9)
    daily_summary_minute: int = _env_int("DAILY_SUMMARY_MINUTE", 0)
    reminder_scan_interval_minutes: int = _env_int("REMINDER_SCAN_INTERVAL_MINUTES", 5)

    database_url: str = os.getenv("DATABASE_URL") or "sqlite:///./backend/data/recruit.db"

    app_timezone: str = os.getenv("APP_TIMEZONE") or "Asia/Shanghai"

    @property
    def tencent_docs_configured(self) -> bool:
        return bool(
            self.tencent_docs_client_id
            and self.tencent_docs_access_token
            and self.tencent_docs_open_id
        )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)


settings = Settings()

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
