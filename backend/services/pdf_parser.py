from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader

from ..config import UPLOAD_DIR


TEXT_PDF_ONLY_MESSAGE = "当前版本仅支持文本型 PDF，扫描件后续可接入 OCR"


def safe_filename(filename: str) -> str:
    stem = Path(filename).stem or "resume"
    suffix = Path(filename).suffix.lower() or ".pdf"
    stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5._-]+", "_", stem).strip("._") or "resume"
    return f"{stem}_{uuid4().hex[:12]}{suffix}"


def save_upload_file(file: UploadFile) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / safe_filename(file.filename or "resume.pdf")
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return target


def extract_pdf_text(path: str | Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text.strip())
    raw_text = "\n\n".join(chunks).strip()
    if not raw_text:
        raise ValueError(TEXT_PDF_ONLY_MESSAGE)
    return raw_text
