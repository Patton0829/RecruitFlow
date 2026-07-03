from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ParseLog
from ..schemas import ResumeParseResponse
from ..services.pdf_parser import TEXT_PDF_ONLY_MESSAGE, extract_pdf_text, save_upload_file
from ..services.resume_extractor import ResumeExtractor


router = APIRouter()


@router.post("/parse", response_model=ResumeParseResponse)
def parse_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 简历文件。")

    saved_path = save_upload_file(file)
    try:
        raw_text = extract_pdf_text(saved_path)
    except ValueError as exc:
        db.add(
            ParseLog(
                file_name=file.filename or saved_path.name,
                llm_input_preview="",
                llm_output_json="",
                success=False,
                error_message=str(exc),
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail=TEXT_PDF_ONLY_MESSAGE) from exc
    except Exception as exc:
        db.add(
            ParseLog(
                file_name=file.filename or saved_path.name,
                llm_input_preview="",
                llm_output_json="",
                success=False,
                error_message=str(exc),
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"PDF 解析失败：{exc}") from exc

    try:
        result = ResumeExtractor().extract(raw_text)
        db.add(
            ParseLog(
                file_name=file.filename or saved_path.name,
                llm_input_preview=raw_text[:1000],
                llm_output_json=result.raw_output,
                success=True,
            )
        )
        db.commit()
    except Exception as exc:
        db.add(
            ParseLog(
                file_name=file.filename or saved_path.name,
                llm_input_preview=raw_text[:1000],
                llm_output_json=json.dumps({}, ensure_ascii=False),
                success=False,
                error_message=str(exc),
            )
        )
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI 简历解析失败：{exc}") from exc

    return ResumeParseResponse(
        success=True,
        file_path=str(saved_path),
        raw_text_preview=raw_text[:500],
        raw_resume_text=raw_text,
        parsed=result.parsed,
        parser_mode=result.parser_mode,
    )
