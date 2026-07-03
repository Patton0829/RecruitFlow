from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ..schemas import ParsedResume
from .llm_client import LLMClient


PROMPT_TEMPLATE = """你是一个 HR 招聘简历解析助手。请从候选人简历文本中抽取结构化信息。

你只能根据简历原文抽取，不要编造简历中没有的信息。

请严格输出 JSON，不要输出 Markdown，不要输出解释。

需要输出的 JSON 字段如下：
{{
  "name": string | null,
  "phone": string | null,
  "email": string | null,
  "school": string | null,
  "degree": string | null,
  "major": string | null,
  "graduation_year": string | null,
  "city": string | null,
  "skills": string[],
  "resume_summary": string | null,
  "project_summary": string | null,
  "confidence": number,
  "missing_fields": string[]
}}

字段说明：
- name：候选人姓名。
- phone：手机号。
- email：邮箱。
- school：最高学历或最近教育经历对应学校。
- degree：最高学历，例如本科、硕士、博士。
- major：专业。
- graduation_year：毕业年份。
- city：候选人所在城市，如果简历没有写则为 null。
- skills：候选人技能标签，最多 12 个。
- resume_summary：候选人经历摘要，不超过 100 字。
- project_summary：核心项目或实习经历摘要，不超过 150 字。
- confidence：你对解析结果的置信度，范围 0 到 1。
- missing_fields：简历中缺失但招聘录入常用的重要字段。

简历文本如下：
{resume_text}
"""


@dataclass
class ExtractedResume:
    parsed: ParsedResume
    raw_output: str
    parser_mode: str


class ResumeExtractor:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def extract(self, resume_text: str) -> ExtractedResume:
        prompt = PROMPT_TEMPLATE.format(resume_text=resume_text[:12000])
        if self.llm_client.configured:
            raw_output = self.llm_client.complete(prompt)
            parsed = self._parse_llm_output(raw_output)
            return ExtractedResume(parsed=parsed, raw_output=raw_output, parser_mode="llm")

        parsed = self._fallback_extract(resume_text)
        raw_output = parsed.model_dump_json(ensure_ascii=False)
        return ExtractedResume(parsed=parsed, raw_output=raw_output, parser_mode="local_mock")

    def _parse_llm_output(self, raw_output: str) -> ParsedResume:
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            payload: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            payload = json.loads(match.group(0))

        try:
            return ParsedResume.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"LLM 输出未通过结构化校验: {exc}") from exc

    def _fallback_extract(self, resume_text: str) -> ParsedResume:
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        joined = "\n".join(lines)

        phone = self._first_match(r"(?<!\d)(?:\+?86[-\s]?)?(1[3-9]\d{9})(?!\d)", joined)
        email = self._first_match(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", joined)
        name = self._label_match(joined, ["姓名", "Name"]) or self._guess_name(lines)
        school = self._label_match(joined, ["学校", "院校", "毕业院校"]) or self._guess_school(lines)
        degree = self._guess_degree(joined)
        major = self._label_match(joined, ["专业", "Major"])
        graduation_year = self._first_match(r"(?:毕业时间|毕业年份|毕业|届)[:：\s]*(20\d{2})", joined)
        if not graduation_year:
            graduation_year = self._first_match(r"\b(20\d{2})\b", joined)
        city = self._label_match(joined, ["所在城市", "现居地", "居住地", "城市"])
        skills = self._guess_skills(joined)
        resume_summary = self._summary_from_text(lines, 100)
        project_summary = self._project_summary(lines)

        payload = {
            "name": name,
            "phone": phone,
            "email": email,
            "school": school,
            "degree": degree,
            "major": major,
            "graduation_year": graduation_year,
            "city": city,
            "skills": skills,
            "resume_summary": resume_summary,
            "project_summary": project_summary,
            "confidence": 0.35,
        }
        missing_fields = [
            key
            for key in ["name", "phone", "email", "school", "degree", "major"]
            if not payload.get(key)
        ]
        payload["missing_fields"] = missing_fields
        return ParsedResume.model_validate(payload)

    @staticmethod
    def _first_match(pattern: str, text: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1) if match and match.groups() else (match.group(0) if match else None)

    @staticmethod
    def _label_match(text: str, labels: list[str]) -> str | None:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n｜|,，;；]{{1,80}})"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _guess_name(lines: list[str]) -> str | None:
        for line in lines[:8]:
            compact = re.sub(r"\s+", "", line)
            if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", compact):
                if compact not in {"个人简历", "简历", "求职简历"}:
                    return compact
        return None

    @staticmethod
    def _guess_school(lines: list[str]) -> str | None:
        for line in lines:
            match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9·]{2,40}(?:大学|学院|学校|University|College))", line)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _guess_degree(text: str) -> str | None:
        for degree in ["博士", "硕士", "研究生", "本科", "大专", "专科"]:
            if degree in text:
                return "硕士" if degree == "研究生" else degree
        return None

    @staticmethod
    def _guess_skills(text: str) -> list[str]:
        candidates = [
            "Python",
            "Java",
            "Go",
            "C++",
            "JavaScript",
            "TypeScript",
            "FastAPI",
            "Django",
            "Flask",
            "Spring",
            "React",
            "Vue",
            "MySQL",
            "PostgreSQL",
            "Redis",
            "Docker",
            "Kubernetes",
            "Linux",
            "SQL",
            "PyTorch",
            "TensorFlow",
            "机器学习",
            "深度学习",
            "数据分析",
            "NLP",
            "LLM",
        ]
        found: list[str] = []
        lowered = text.lower()
        for skill in candidates:
            if skill.lower() in lowered and skill not in found:
                found.append(skill)
            if len(found) >= 12:
                break
        return found

    @staticmethod
    def _summary_from_text(lines: list[str], max_len: int) -> str | None:
        useful = [line for line in lines if len(line) >= 8 and not re.search(r"电话|邮箱|手机", line)]
        if not useful:
            return None
        summary = "；".join(useful[:3])
        return summary[:max_len]

    @staticmethod
    def _project_summary(lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if any(keyword in line for keyword in ["项目", "实习", "经历"]):
                summary = "；".join(lines[index : index + 4])
                return summary[:150]
        return None
