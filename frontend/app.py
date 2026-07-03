from __future__ import annotations

import hashlib
import os
import re
import time as time_module
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

FLOW_STAGE_OPTIONS = ["一轮面试", "二轮面试", "offer发放"]

APPLICATION_STATUS = ["进行中", "已通过", "已淘汰", "已放弃", "人才库"]
HR_DECISIONS = ["待决定", "推进下一轮", "暂不推进", "发Offer", "淘汰", "进入人才库"]
HR_OPTIONS = ["张三", "李四", "王五", "赵六", "王王"]
INTERVIEWER_OPTIONS = ["李工", "王工", "张工", "赵经理", "李四"]

SCHOOL_CITY_HINTS = {
    "西安": "西安",
    "北京": "北京",
    "上海": "上海",
    "天津": "天津",
    "重庆": "重庆",
    "南京": "南京",
    "杭州": "杭州",
    "广州": "广州",
    "深圳": "深圳",
    "成都": "成都",
    "武汉": "武汉",
    "长沙": "长沙",
    "郑州": "郑州",
    "济南": "济南",
    "青岛": "青岛",
    "合肥": "合肥",
    "南昌": "南昌",
    "福州": "福州",
    "厦门": "厦门",
    "哈尔滨": "哈尔滨",
    "长春": "长春",
    "沈阳": "沈阳",
    "大连": "大连",
    "太原": "太原",
    "石家庄": "石家庄",
    "呼和浩特": "呼和浩特",
    "兰州": "兰州",
    "银川": "银川",
    "西宁": "西宁",
    "乌鲁木齐": "乌鲁木齐",
    "昆明": "昆明",
    "贵阳": "贵阳",
    "南宁": "南宁",
    "海口": "海口",
    "苏州": "苏州",
    "无锡": "无锡",
    "宁波": "宁波",
    "珠海": "珠海",
}


def api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def show_response_error(response: requests.Response) -> None:
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    st.error(detail)


def split_skills(value: str) -> list[str]:
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def split_people(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[、,，;；/\n]+", value) if item.strip()]


def unique_people(items: list[str]) -> list[str]:
    seen: set[str] = set()
    people: list[str] = []
    for item in items:
        if item and item not in seen:
            people.append(item)
            seen.add(item)
    return people


def join_people(selected: list[str], custom_text: str | None = None) -> str:
    return "、".join(unique_people([*selected, *split_people(custom_text)]))


def people_multiselect(
    label: str,
    options: list[str],
    current_value: str | None,
    key_prefix: str,
) -> str:
    current_people = split_people(current_value)
    selected_defaults = [person for person in current_people if person in options]
    custom_defaults = [person for person in current_people if person not in options]
    selected = st.multiselect(
        label,
        options,
        default=selected_defaults,
        key=f"{key_prefix}_select",
    )
    custom = st.text_input(
        f"其他{label}",
        value="、".join(custom_defaults),
        key=f"{key_prefix}_custom",
        placeholder="可输入多个，用顿号或逗号分隔",
    )
    return join_people(selected, custom)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def infer_city_from_school(school: str | None) -> str:
    if not school:
        return ""
    for keyword, city in SCHOOL_CITY_HINTS.items():
        if keyword in school:
            return city
    return ""


def resume_pdf_url(result: dict[str, Any]) -> str | None:
    file_path = result.get("file_path")
    if not file_path:
        return None
    return api_url(f"/uploads/{quote(Path(file_path).name)}")


@st.cache_data(show_spinner=False)
def pdf_preview_images(file_path: str, max_pages: int = 2) -> tuple[list[bytes], int]:
    import fitz

    images: list[bytes] = []
    doc = fitz.open(file_path)
    try:
        page_count = doc.page_count
        for page_index in range(min(page_count, max_pages)):
            page = doc.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
            images.append(pixmap.tobytes("png"))
        return images, page_count
    finally:
        doc.close()


def render_pdf_preview(result: dict[str, Any], file_name: str) -> None:
    pdf_url = resume_pdf_url(result)
    if pdf_url:
        st.link_button("新标签打开简历 PDF", pdf_url)

    file_path = result.get("file_path")
    if not file_path:
        st.caption("没有可预览的 PDF 文件。")
        return

    try:
        images, page_count = pdf_preview_images(file_path)
    except ImportError:
        st.warning("当前环境缺少 PyMuPDF，暂时无法在页面内预览 PDF。")
        return
    except Exception as exc:
        st.warning(f"PDF 预览生成失败：{exc}")
        return

    if not images:
        st.caption("PDF 没有可预览页面。")
        return

    for page_index, image in enumerate(images, start=1):
        st.image(image, caption=f"{file_name} 第 {page_index} 页", width="stretch")
    if page_count > len(images):
        st.caption(f"已预览前 {len(images)} 页，共 {page_count} 页。")


def fetch_candidates(params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        response = requests.get(api_url("/api/candidates"), params=params or {}, timeout=20)
    except requests.RequestException as exc:
        st.error(f"无法连接后端：{exc}")
        return []
    if response.ok:
        return response.json()
    show_response_error(response)
    return []


def post_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        response = requests.post(api_url(path), json=payload, timeout=60)
    except requests.RequestException as exc:
        st.error(f"无法连接后端：{exc}")
        return None
    if response.ok:
        return response.json()
    show_response_error(response)
    return None


def patch_json(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        response = requests.patch(api_url(path), json=payload, timeout=30)
    except requests.RequestException as exc:
        st.error(f"无法连接后端：{exc}")
        return None
    if response.ok:
        return response.json()
    show_response_error(response)
    return None


def uploaded_file_key(file: Any, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"{file.name}:{digest}"


def sync_uploaded_resume_state(uploaded_files: list[Any]) -> list[tuple[str, Any, bytes]]:
    parsed_resumes = st.session_state.setdefault("parsed_resumes", {})
    parse_errors = st.session_state.setdefault("parse_errors", {})

    current_files: list[tuple[str, Any, bytes]] = []
    current_keys: set[str] = set()
    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        file_key = uploaded_file_key(uploaded_file, content)
        current_files.append((file_key, uploaded_file, content))
        current_keys.add(file_key)

    for stale_key in set(parsed_resumes) - current_keys:
        parsed_resumes.pop(stale_key, None)
        parse_errors.pop(stale_key, None)
        st.session_state.pop(f"save_response_{stale_key}", None)
    for stale_key in set(parse_errors) - current_keys:
        parse_errors.pop(stale_key, None)

    return current_files


def parse_next_uploaded_resume(current_files: list[tuple[str, Any, bytes]]) -> None:
    parsed_resumes = st.session_state.setdefault("parsed_resumes", {})
    parse_errors = st.session_state.setdefault("parse_errors", {})

    pending_files = [
        item for item in current_files if item[0] not in parsed_resumes and item[0] not in parse_errors
    ]
    if not pending_files:
        if current_files:
            success_count = len(parsed_resumes)
            error_count = len(parse_errors)
            st.success(f"解析完成：成功 {success_count} 份，失败 {error_count} 份。")
        return

    file_key, uploaded_file, content = pending_files[0]
    current_index = next(
        index for index, (candidate_key, _, _) in enumerate(current_files, start=1) if candidate_key == file_key
    )
    total = len(current_files)
    completed_before = total - len(pending_files)
    base_progress = completed_before / total
    per_file_span = 1 / total
    progress = st.progress(0)
    status = st.empty()
    progress.progress(base_progress)
    status.info(f"正在解析 {current_index}/{total}：{uploaded_file.name}｜读取上传文件")
    for offset, label in [
        (0.10, "读取上传文件"),
        (0.24, "提取 PDF 文本"),
        (0.42, "调用 AI 解析"),
    ]:
        time_module.sleep(0.35)
        progress.progress(min(base_progress + per_file_span * offset, 0.98))
        status.info(f"正在解析 {current_index}/{total}：{uploaded_file.name}｜{label}")

    files = {"file": (uploaded_file.name, content, "application/pdf")}
    try:
        response = requests.post(api_url("/api/resumes/parse"), files=files, timeout=90)
    except requests.RequestException as exc:
        parse_errors[file_key] = f"无法连接后端：{exc}"
    else:
        if response.ok:
            result = response.json()
            result["uploaded_name"] = uploaded_file.name
            result["uploaded_pdf_bytes"] = content
            parsed_resumes[file_key] = result
        else:
            try:
                parse_errors[file_key] = response.json().get("detail", response.text)
            except ValueError:
                parse_errors[file_key] = response.text

    progress.progress(min(base_progress + per_file_span * 0.82, 0.98))
    status.info(f"正在解析 {current_index}/{total}：{uploaded_file.name}｜生成确认表单")
    time_module.sleep(0.35)
    progress.progress((completed_before + 1) / total)
    time_module.sleep(0.2)
    st.rerun()


def render_resume_confirm_form(result: dict[str, Any], result_key: str, prefix: str) -> None:
    parsed = result["parsed"]
    file_name = result.get("uploaded_name") or Path(result.get("file_path", "简历")).name

    with st.expander(f"{file_name}｜解析结果确认", expanded=True):
        st.subheader("上传简历")
        render_pdf_preview(result, file_name)
        st.subheader("解析结果确认")
        st.caption(
            f"解析模式：{result.get('parser_mode', 'unknown')}｜"
            f"置信度：{parsed.get('confidence', 0):.2f}"
        )
        missing_fields = parsed.get("missing_fields") or []
        if missing_fields:
            st.warning("缺失字段：" + "、".join(missing_fields))
        with st.expander("PDF 文本预览", expanded=False):
            st.text(result.get("raw_text_preview", ""))

        with st.form(f"confirm_candidate_form_{prefix}"):
            st.subheader("候选人信息")
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("姓名", value=parsed.get("name") or "", key=f"{prefix}_name")
                phone = st.text_input("手机号", value=parsed.get("phone") or "", key=f"{prefix}_phone")
                email = st.text_input("邮箱", value=parsed.get("email") or "", key=f"{prefix}_email")
            with col2:
                school = st.text_input("学校", value=parsed.get("school") or "", key=f"{prefix}_school")
                degree = st.text_input("学历", value=parsed.get("degree") or "", key=f"{prefix}_degree")
                major = st.text_input("专业", value=parsed.get("major") or "", key=f"{prefix}_major")
            with col3:
                default_city = parsed.get("city") or infer_city_from_school(parsed.get("school"))
                city = st.text_input("所在城市", value=default_city, key=f"{prefix}_city")
                skills_text = st.text_input(
                    "技能标签",
                    value=", ".join(parsed.get("skills") or []),
                    key=f"{prefix}_skills",
                )

            resume_summary = st.text_area(
                "候选人经历摘要",
                value=parsed.get("resume_summary") or "",
                height=90,
                key=f"{prefix}_resume_summary",
            )
            project_summary = st.text_area(
                "项目/实习摘要",
                value=parsed.get("project_summary") or "",
                height=110,
                key=f"{prefix}_project_summary",
            )

            st.subheader("招聘流程")
            col4, col5, col6 = st.columns(3)
            with col4:
                position = st.text_input("应聘岗位", value="", key=f"{prefix}_position")
                source = st.text_input("招聘来源", value="BOSS直聘", key=f"{prefix}_source")
                stage = st.selectbox(
                    "当前阶段",
                    FLOW_STAGE_OPTIONS,
                    index=0,
                    key=f"{prefix}_stage",
                )
            with col5:
                status = st.selectbox("状态", APPLICATION_STATUS, index=0, key=f"{prefix}_status")
                hr_decision = st.selectbox(
                    "HR 决策", HR_DECISIONS, index=0, key=f"{prefix}_hr_decision"
                )
            with col6:
                owner_hr_value = people_multiselect(
                    "负责 HR",
                    HR_OPTIONS,
                    "",
                    f"{prefix}_owner_hr",
                )
                interviewer_value = people_multiselect(
                    "面试官",
                    INTERVIEWER_OPTIONS,
                    "",
                    f"{prefix}_interviewer",
                )

            interview_time_value: str | None = None
            if stage in {"一轮面试", "二轮面试"}:
                st.markdown(f"**预约{stage}时间**")
                time_col1, time_col2 = st.columns(2)
                with time_col1:
                    interview_date = st.date_input(
                        "预约日期", value=date.today(), key=f"{prefix}_interview_date"
                    )
                with time_col2:
                    interview_clock = st.time_input(
                        "预约时间",
                        value=time(hour=10, minute=0),
                        key=f"{prefix}_interview_clock",
                    )
                interview_time_value = datetime.combine(interview_date, interview_clock).isoformat()

            next_action = st.text_input("下一步动作", value="", key=f"{prefix}_next_action")
            notes = st.text_area("备注", value="", height=100, key=f"{prefix}_notes")

            submitted = st.form_submit_button("确认保存并同步腾讯文档", type="primary")
            if submitted:
                if not position.strip() or not owner_hr_value.strip():
                    st.error("应聘岗位和负责 HR 必填。")
                else:
                    payload = {
                        "candidate": {
                            "name": none_if_blank(name),
                            "phone": none_if_blank(phone),
                            "email": none_if_blank(email),
                            "school": none_if_blank(school),
                            "degree": none_if_blank(degree),
                            "major": none_if_blank(major),
                            "graduation_year": None,
                            "city": none_if_blank(city),
                            "skills": split_skills(skills_text),
                            "resume_summary": none_if_blank(resume_summary),
                            "project_summary": none_if_blank(project_summary),
                            "resume_file_path": result.get("file_path"),
                            "raw_resume_text": result.get("raw_resume_text"),
                        },
                        "application": {
                            "position": position.strip(),
                            "source": source.strip() or "未知",
                            "stage": stage,
                            "status": status,
                            "owner_hr": owner_hr_value.strip(),
                            "interviewer": none_if_blank(interviewer_value),
                            "interview_time": interview_time_value,
                            "interview_round": None,
                            "next_action": none_if_blank(next_action),
                            "hr_decision": hr_decision,
                            "notes": none_if_blank(notes),
                        },
                    }
                    response = post_json("/api/candidates/confirm", payload)
                    if response:
                        st.session_state[f"save_response_{result_key}"] = response
                        st.success(
                            "保存成功："
                            f"candidate_id={response['candidate_id']}，"
                            f"application_id={response['application_id']}，"
                            f"同步腾讯文档={response['synced_to_tencent_docs']}"
                        )
                        if response.get("matched_existing"):
                            st.info(f"已关联已有候选人，匹配方式：{response.get('match_type')}")
                        if response.get("tencent_docs_url"):
                            st.link_button("打开腾讯文档台账", response["tencent_docs_url"])

        saved_response = st.session_state.get(f"save_response_{result_key}")
        if saved_response:
            st.info(
                "已保存："
                f"candidate_id={saved_response['candidate_id']}，"
                f"application_id={saved_response['application_id']}"
            )
            if saved_response.get("tencent_docs_url"):
                st.link_button("打开腾讯文档台账", saved_response["tencent_docs_url"])


def page_upload_resume() -> None:
    st.title("上传简历")
    uploaded_files = st.file_uploader(
        "上传候选人 PDF 简历，可一次选择多份",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        return

    current_files = sync_uploaded_resume_state(uploaded_files)

    parsed_resumes = st.session_state.get("parsed_resumes", {})
    parse_errors = st.session_state.get("parse_errors", {})
    if parse_errors:
        st.subheader("解析失败")
        for file_key, error in parse_errors.items():
            st.error(f"{file_key.split(':', 1)[0]}：{error}")

    if not parsed_resumes:
        parse_next_uploaded_resume(current_files)
        return

    st.subheader("已上传简历")
    for index, (result_key, result) in enumerate(parsed_resumes.items(), start=1):
        prefix = f"resume_{index}_{hashlib.sha256(result_key.encode()).hexdigest()[:12]}"
        render_resume_confirm_form(result, result_key, prefix)

    parse_next_uploaded_resume(current_files)


def page_candidate_list() -> None:
    import pandas as pd

    st.title("候选人列表")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        stage = st.selectbox("阶段筛选", ["全部"] + FLOW_STAGE_OPTIONS)
    with filter_col2:
        status = st.selectbox("状态筛选", ["全部"] + APPLICATION_STATUS)
    with filter_col3:
        position = st.text_input("岗位关键词")
    with filter_col4:
        source = st.text_input("来源")

    params = {
        "stage": None if stage == "全部" else stage,
        "status": None if status == "全部" else status,
        "position": position.strip() or None,
        "source": source.strip() or None,
    }
    params = {key: value for key, value in params.items() if value}
    data = fetch_candidates(params)

    if not data:
        st.info("暂无候选人记录。")
        return

    df = pd.DataFrame(data)
    display_columns = [
        "name",
        "position",
        "source",
        "school",
        "degree",
        "major",
        "stage",
        "status",
        "interview_time",
        "interviewer",
        "owner_hr",
        "next_action",
        "updated_at",
    ]
    st.dataframe(
        df[display_columns].rename(
            columns={
                "name": "姓名",
                "position": "岗位",
                "source": "来源",
                "school": "学校",
                "degree": "学历",
                "major": "专业",
                "stage": "当前阶段",
                "status": "状态",
                "interview_time": "面试时间",
                "interviewer": "面试官",
                "owner_hr": "负责 HR",
                "next_action": "下一步动作",
                "updated_at": "更新时间",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("编辑招聘流程")
    options = {
        f"#{row['application_id']}｜{row.get('name') or '候选人'}｜{row['position']}｜{row['stage']}": row
        for row in data
    }
    selected_label = st.selectbox("选择记录", list(options.keys()))
    selected = options[selected_label]

    with st.form("edit_application_form"):
        edit_col1, edit_col2, edit_col3 = st.columns(3)
        with edit_col1:
            new_stage = st.selectbox(
                "阶段",
                FLOW_STAGE_OPTIONS,
                index=FLOW_STAGE_OPTIONS.index(selected["stage"])
                if selected["stage"] in FLOW_STAGE_OPTIONS
                else 0,
            )
            new_status = st.selectbox(
                "状态",
                APPLICATION_STATUS,
                index=APPLICATION_STATUS.index(selected["status"])
                if selected["status"] in APPLICATION_STATUS
                else 0,
            )
            new_hr_decision = st.selectbox(
                "HR 决策",
                HR_DECISIONS,
                index=HR_DECISIONS.index(selected.get("hr_decision"))
                if selected.get("hr_decision") in HR_DECISIONS
                else 0,
            )
        with edit_col2:
            new_owner_hr = people_multiselect(
                "负责 HR",
                HR_OPTIONS,
                selected.get("owner_hr"),
                f"edit_{selected['application_id']}_owner_hr",
            )
            new_interviewer = people_multiselect(
                "面试官",
                INTERVIEWER_OPTIONS,
                selected.get("interviewer"),
                f"edit_{selected['application_id']}_interviewer",
            )
        with edit_col3:
            current_dt = parse_datetime(selected.get("interview_time"))
            if new_stage in {"一轮面试", "二轮面试"}:
                st.markdown(f"**预约{new_stage}时间**")
                new_date = st.date_input(
                    "预约日期", value=current_dt.date() if current_dt else date.today()
                )
                new_time = st.time_input(
                    "预约时间", value=current_dt.time() if current_dt else time(hour=10)
                )
            else:
                new_date = None
                new_time = None

        new_next_action = st.text_input("下一步动作", value=selected.get("next_action") or "")
        new_notes = st.text_area("备注", value=selected.get("notes") or "", height=100)
        submitted = st.form_submit_button("保存更新", type="primary")
        if submitted:
            if not new_owner_hr.strip():
                st.error("负责 HR 必填。")
                return
            interview_time_value = (
                datetime.combine(new_date, new_time).isoformat()
                if new_stage in {"一轮面试", "二轮面试"} and new_date and new_time
                else None
            )
            payload = {
                "stage": new_stage,
                "status": new_status,
                "interview_time": interview_time_value,
                "interviewer": none_if_blank(new_interviewer),
                "owner_hr": new_owner_hr.strip(),
                "interview_round": None,
                "next_action": none_if_blank(new_next_action),
                "hr_decision": new_hr_decision,
                "notes": none_if_blank(new_notes),
            }
            updated = patch_json(f"/api/applications/{selected['application_id']}", payload)
            if updated:
                st.success("更新成功，并已同步腾讯文档。")
                st.rerun()


def page_dashboard() -> None:
    import pandas as pd

    st.title("招聘看板")
    try:
        response = requests.get(api_url("/api/dashboard/summary"), timeout=20)
    except requests.RequestException as exc:
        st.error(f"无法连接后端：{exc}")
        return
    if not response.ok:
        show_response_error(response)
        return

    summary = response.json()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("总候选人", summary["total_candidates"])
    col2.metric("进行中", summary["active_applications"])
    col3.metric("今日面试", summary["today_interviews"])
    col4.metric("未来 1 小时", summary["upcoming_1h_interviews"])
    col5.metric("超时未跟进", summary["overdue_followups"])

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("阶段分布")
        stage_counts = summary.get("stage_counts") or {}
        if stage_counts:
            st.bar_chart(pd.DataFrame.from_dict(stage_counts, orient="index", columns=["数量"]))
        else:
            st.info("暂无阶段数据。")
    with chart_col2:
        st.subheader("来源分布")
        source_counts = summary.get("source_counts") or {}
        if source_counts:
            st.bar_chart(pd.DataFrame.from_dict(source_counts, orient="index", columns=["数量"]))
        else:
            st.info("暂无来源数据。")

    st.subheader("今日面试列表")
    today_list = summary.get("today_interview_list") or []
    if today_list:
        today_df = pd.DataFrame(today_list)
        st.dataframe(
            today_df[
                ["name", "position", "interview_time", "interviewer", "owner_hr"]
            ].rename(
                columns={
                    "name": "姓名",
                    "position": "岗位",
                    "interview_time": "面试时间",
                    "interviewer": "面试官",
                    "owner_hr": "负责 HR",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("今日暂无面试。")


def page_reminders() -> None:
    st.title("面试提醒测试")
    st.caption("未配置 WECOM_WEBHOOK_URL 时，提醒内容会打印在后端控制台。")

    actions = [
        ("发送测试企业微信群消息", "/api/reminders/test-wecom"),
        ("手动发送今日面试汇总", "/api/reminders/send-daily-summary"),
        ("手动扫描面试前 1 小时提醒", "/api/reminders/scan-upcoming"),
    ]
    for label, path in actions:
        if st.button(label, key=path):
            result = post_json(path)
            if result:
                st.success(result["message"])
                for log in result.get("logs", []):
                    st.code(log, language="text")


def main() -> None:
    st.set_page_config(page_title="RecruitFlow AI｜招聘流程提效助手", layout="wide")
    st.sidebar.title("RecruitFlow AI｜招聘流程提效助手")
    page = st.sidebar.radio("功能", ["上传简历", "候选人列表", "招聘看板", "面试提醒测试"])
    st.sidebar.caption(f"后端：{API_BASE_URL}")

    if page == "上传简历":
        page_upload_resume()
    elif page == "候选人列表":
        page_candidate_list()
    elif page == "招聘看板":
        page_dashboard()
    else:
        page_reminders()


if __name__ == "__main__":
    main()
