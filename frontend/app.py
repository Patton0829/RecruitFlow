from __future__ import annotations

import hashlib
import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

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


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


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


def parse_uploaded_resumes(uploaded_files: list[Any]) -> None:
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

    pending_files = [
        item for item in current_files if item[0] not in parsed_resumes and item[0] not in parse_errors
    ]
    if not pending_files:
        return

    progress = st.progress(0)
    status = st.empty()
    total = len(pending_files)
    for index, (file_key, uploaded_file, content) in enumerate(pending_files, start=1):
        status.info(f"正在解析 {index}/{total}：{uploaded_file.name}")
        files = {"file": (uploaded_file.name, content, "application/pdf")}
        try:
            response = requests.post(api_url("/api/resumes/parse"), files=files, timeout=90)
        except requests.RequestException as exc:
            parse_errors[file_key] = f"无法连接后端：{exc}"
        else:
            if response.ok:
                result = response.json()
                result["uploaded_name"] = uploaded_file.name
                parsed_resumes[file_key] = result
            else:
                try:
                    parse_errors[file_key] = response.json().get("detail", response.text)
                except ValueError:
                    parse_errors[file_key] = response.text
        progress.progress(index / total)

    status.success(f"解析完成：成功 {len(parsed_resumes)} 份，失败 {len(parse_errors)} 份。")


def render_resume_confirm_form(result: dict[str, Any], result_key: str, prefix: str) -> None:
    parsed = result["parsed"]
    file_name = result.get("uploaded_name") or Path(result.get("file_path", "简历")).name

    with st.expander(f"{file_name}｜解析结果确认", expanded=True):
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
                graduation_year = st.text_input(
                    "毕业年份",
                    value=parsed.get("graduation_year") or "",
                    key=f"{prefix}_graduation_year",
                )
                city = st.text_input("所在城市", value=parsed.get("city") or "", key=f"{prefix}_city")
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
                    RECRUIT_STAGES,
                    index=RECRUIT_STAGES.index("待筛选"),
                    key=f"{prefix}_stage",
                )
            with col5:
                status = st.selectbox("状态", APPLICATION_STATUS, index=0, key=f"{prefix}_status")
                hr_decision = st.selectbox(
                    "HR 决策", HR_DECISIONS, index=0, key=f"{prefix}_hr_decision"
                )
                interview_round = st.text_input("面试轮次", value="", key=f"{prefix}_round")
            with col6:
                owner_hr = st.text_input("负责 HR", value="", key=f"{prefix}_owner_hr")
                interviewer = st.text_input("面试官", value="", key=f"{prefix}_interviewer")
                has_interview_time = st.checkbox(
                    "已约面试时间", value=False, key=f"{prefix}_has_interview_time"
                )

            interview_time_value: str | None = None
            if has_interview_time:
                time_col1, time_col2 = st.columns(2)
                with time_col1:
                    interview_date = st.date_input(
                        "面试日期", value=date.today(), key=f"{prefix}_interview_date"
                    )
                with time_col2:
                    interview_clock = st.time_input(
                        "面试时间",
                        value=time(hour=10, minute=0),
                        key=f"{prefix}_interview_clock",
                    )
                interview_time_value = datetime.combine(interview_date, interview_clock).isoformat()

            next_action = st.text_input("下一步动作", value="", key=f"{prefix}_next_action")
            notes = st.text_area("备注", value="", height=100, key=f"{prefix}_notes")

            submitted = st.form_submit_button("确认保存并同步腾讯文档", type="primary")
            if submitted:
                if not position.strip() or not owner_hr.strip():
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
                            "graduation_year": none_if_blank(graduation_year),
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
                            "owner_hr": owner_hr.strip(),
                            "interviewer": none_if_blank(interviewer),
                            "interview_time": interview_time_value,
                            "interview_round": none_if_blank(interview_round),
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

        saved_response = st.session_state.get(f"save_response_{result_key}")
        if saved_response:
            st.info(
                "已保存："
                f"candidate_id={saved_response['candidate_id']}，"
                f"application_id={saved_response['application_id']}"
            )


def page_upload_resume() -> None:
    st.title("上传简历")
    uploaded_files = st.file_uploader(
        "上传候选人 PDF 简历，可一次选择多份",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.info("选择 PDF 后系统会自动提取文本并解析，不需要额外点击解析按钮。")
        return

    parse_uploaded_resumes(uploaded_files)

    parsed_resumes = st.session_state.get("parsed_resumes", {})
    parse_errors = st.session_state.get("parse_errors", {})
    if parse_errors:
        st.subheader("解析失败")
        for file_key, error in parse_errors.items():
            st.error(f"{file_key.split(':', 1)[0]}：{error}")

    if not parsed_resumes:
        return

    st.subheader("解析结果确认")
    for index, (result_key, result) in enumerate(parsed_resumes.items(), start=1):
        prefix = f"resume_{index}_{hashlib.sha256(result_key.encode()).hexdigest()[:12]}"
        render_resume_confirm_form(result, result_key, prefix)


def page_candidate_list() -> None:
    st.title("候选人列表")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        stage = st.selectbox("阶段筛选", ["全部"] + RECRUIT_STAGES)
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
        use_container_width=True,
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
                RECRUIT_STAGES,
                index=RECRUIT_STAGES.index(selected["stage"])
                if selected["stage"] in RECRUIT_STAGES
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
            new_interviewer = st.text_input("面试官", value=selected.get("interviewer") or "")
            new_owner_hr = st.text_input("负责 HR", value=selected.get("owner_hr") or "")
            new_round = st.text_input("面试轮次", value=selected.get("interview_round") or "")
        with edit_col3:
            current_dt = parse_datetime(selected.get("interview_time"))
            set_interview_time = st.checkbox("设置面试时间", value=current_dt is not None)
            if set_interview_time:
                new_date = st.date_input(
                    "面试日期", value=current_dt.date() if current_dt else date.today()
                )
                new_time = st.time_input(
                    "面试时间", value=current_dt.time() if current_dt else time(hour=10)
                )
            else:
                new_date = None
                new_time = None

        new_next_action = st.text_input("下一步动作", value=selected.get("next_action") or "")
        new_notes = st.text_area("备注", value=selected.get("notes") or "", height=100)
        submitted = st.form_submit_button("保存更新", type="primary")
        if submitted:
            interview_time_value = (
                datetime.combine(new_date, new_time).isoformat()
                if set_interview_time and new_date and new_time
                else None
            )
            payload = {
                "stage": new_stage,
                "status": new_status,
                "interview_time": interview_time_value,
                "interviewer": none_if_blank(new_interviewer),
                "owner_hr": none_if_blank(new_owner_hr),
                "interview_round": none_if_blank(new_round),
                "next_action": none_if_blank(new_next_action),
                "hr_decision": new_hr_decision,
                "notes": none_if_blank(new_notes),
            }
            updated = patch_json(f"/api/applications/{selected['application_id']}", payload)
            if updated:
                st.success("更新成功，并已同步腾讯文档 mock。")
                st.rerun()


def page_dashboard() -> None:
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
                ["name", "position", "interview_round", "interview_time", "interviewer", "owner_hr"]
            ].rename(
                columns={
                    "name": "姓名",
                    "position": "岗位",
                    "interview_round": "轮次",
                    "interview_time": "面试时间",
                    "interviewer": "面试官",
                    "owner_hr": "负责 HR",
                }
            ),
            use_container_width=True,
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
