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
POSITION_OPTIONS = [
    "AI管培生",
    "Java后端",
    "Python后端",
    "前端开发",
    "测试开发",
    "算法工程师",
    "产品经理",
]
MODULE_PAGES = {
    "简历处理": "上传简历",
    "候选人管理": "候选人列表",
    "数据运营": "招聘看板",
    "通知提醒": "面试提醒测试",
}
MODULE_OPTIONS = list(MODULE_PAGES)

GLOBAL_STYLES = """
<style>
:root {
    --rf-bg: #f5f7fb;
    --rf-panel: #ffffff;
    --rf-panel-soft: #f8fafc;
    --rf-border: #dfe6ef;
    --rf-border-strong: #cbd5e1;
    --rf-text: #202534;
    --rf-muted: #697386;
    --rf-accent: #ff4f4f;
    --rf-accent-dark: #e43d3d;
    --rf-blue: #2563eb;
    --rf-green: #16a34a;
    --rf-sidebar: #171c2a;
}

.stApp {
    background:
        radial-gradient(circle at 18% 0%, rgba(37, 99, 235, 0.06), transparent 28rem),
        linear-gradient(180deg, #fbfcff 0%, var(--rf-bg) 42%, #eef3f8 100%);
    color: var(--rf-text);
}

#MainMenu,
footer,
[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1480px;
    padding-top: 2.25rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    color: var(--rf-text);
    letter-spacing: 0;
}

h1 {
    font-size: 2.45rem !important;
    line-height: 1.15 !important;
    margin-bottom: 1.15rem !important;
}

h2 {
    font-size: 1.6rem !important;
    margin-top: 1.2rem !important;
}

h3 {
    font-size: 1.15rem !important;
}

p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
    color: var(--rf-muted);
}

[data-testid="stSidebar"] {
    background: var(--rf-sidebar);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 2rem 1.35rem;
}

.rf-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.15rem 0 1.3rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
    margin-bottom: 1.25rem;
}

.rf-brand-mark {
    width: 2.35rem;
    height: 2.35rem;
    border-radius: 0.5rem;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, var(--rf-accent), #ff8a5c);
    color: #fff;
    font-weight: 800;
    font-size: 0.95rem;
}

.rf-brand-title {
    color: #fff;
    font-weight: 760;
    font-size: 1.15rem;
    line-height: 1.15;
}

.rf-brand-subtitle {
    color: rgba(255, 255, 255, 0.68);
    font-size: 0.82rem;
    margin-top: 0.18rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: rgba(255, 255, 255, 0.76);
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 0.2rem;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
    min-height: 2.25rem;
    padding: 0;
    margin: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
}

[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
    display: none;
}

[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
    margin: 0;
    padding: 0.4rem 0 0.4rem 0.85rem;
    border-left: 2px solid transparent;
    color: rgba(255, 255, 255, 0.62);
    font-size: 0.92rem;
    font-weight: 620;
}

[data-testid="stSidebar"] [role="radiogroup"] label:hover [data-testid="stMarkdownContainer"] p {
    color: #ffffff;
    border-left-color: rgba(255, 255, 255, 0.35);
}

[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #ffffff;
    border-left-color: var(--rf-accent);
    font-weight: 760;
}

[data-testid="stFileUploader"] section {
    background: var(--rf-panel);
    border: 1px dashed var(--rf-border-strong);
    border-radius: 0.65rem;
    padding: 1.05rem;
}

[data-testid="stFileUploader"] section:hover {
    border-color: var(--rf-blue);
    box-shadow: 0 10px 26px rgba(37, 99, 235, 0.08);
}

.rf-work-visual {
    position: relative;
    min-height: 520px;
    margin-top: 1.6rem;
    overflow: hidden;
    border: 1px solid var(--rf-border);
    border-radius: 0.5rem;
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.20)),
        linear-gradient(135deg, #eef6ff 0%, #f8fbff 46%, #e8f8fb 100%);
    box-shadow: 0 18px 42px rgba(31, 41, 55, 0.06);
}

.rf-work-window {
    position: absolute;
    inset: 9.8rem 2.4rem auto auto;
    width: 44%;
    height: 46%;
    border-radius: 0.5rem;
    background:
        linear-gradient(180deg, rgba(157, 197, 255, 0.38), rgba(255, 255, 255, 0.40)),
        linear-gradient(135deg, #dcecff, #f4fbff);
    border: 1px solid rgba(148, 163, 184, 0.28);
    z-index: 1;
}

.rf-work-window::before {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 42%;
    background:
        linear-gradient(90deg, transparent 0 8%, rgba(30, 41, 59, 0.14) 8% 15%, transparent 15% 23%,
            rgba(30, 41, 59, 0.11) 23% 30%, transparent 30% 39%, rgba(30, 41, 59, 0.16) 39% 47%,
            transparent 47% 58%, rgba(30, 41, 59, 0.13) 58% 66%, transparent 66% 100%);
    opacity: 0.72;
}

.rf-work-sun {
    position: absolute;
    width: 4.8rem;
    height: 4.8rem;
    right: 17%;
    top: 10.9rem;
    border-radius: 50%;
    background: #ffd88a;
    box-shadow: 0 0 34px rgba(255, 196, 87, 0.55);
    animation: rfSun 7s ease-in-out infinite;
    z-index: 2;
}

.rf-work-desk {
    position: absolute;
    left: 6%;
    right: 6%;
    bottom: 3rem;
    height: 4.25rem;
    border-radius: 0.5rem;
    background: linear-gradient(180deg, #ffffff, #dfe8f2);
    border: 1px solid rgba(148, 163, 184, 0.26);
    box-shadow: 0 18px 36px rgba(31, 41, 55, 0.12);
    z-index: 5;
}

.rf-work-laptop {
    position: absolute;
    left: 11%;
    bottom: 6.2rem;
    width: 18rem;
    height: 10.2rem;
    border-radius: 0.5rem 0.5rem 0.28rem 0.28rem;
    background: #20293a;
    border: 0.65rem solid #303b51;
    box-shadow: 0 16px 30px rgba(15, 23, 42, 0.22);
    z-index: 4;
}

.rf-work-laptop::before {
    content: "";
    position: absolute;
    inset: 1.15rem 1.35rem;
    border-radius: 0.35rem;
    background:
        linear-gradient(90deg, rgba(255, 255, 255, 0.20) 0 26%, transparent 26% 100%),
        linear-gradient(180deg, #dceeff, #f5fbff);
}

.rf-work-laptop::after {
    content: "";
    position: absolute;
    left: 22%;
    right: 22%;
    bottom: -1.65rem;
    height: 0.62rem;
    border-radius: 999px;
    background: #94a3b8;
}

.rf-work-person {
    position: absolute;
    left: 28.6rem;
    bottom: 6.5rem;
    width: 5.6rem;
    height: 8.8rem;
    z-index: 4;
}

.rf-work-person::before {
    content: "";
    position: absolute;
    left: 1.95rem;
    top: 0;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 50%;
    background: #f5bd9d;
}

.rf-work-person::after {
    content: "";
    position: absolute;
    left: 1.2rem;
    top: 2.05rem;
    width: 3.2rem;
    height: 5.7rem;
    border-radius: 1.5rem 1.5rem 0.6rem 0.6rem;
    background: linear-gradient(180deg, #4462d8, #273b9f);
}

.rf-work-card {
    position: absolute;
    width: 7.3rem;
    height: 4.7rem;
    border-radius: 0.46rem;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(148, 163, 184, 0.24);
    box-shadow: 0 10px 24px rgba(31, 41, 55, 0.09);
    animation: rfFloatCard 6.5s ease-in-out infinite;
    z-index: 4;
}

.rf-work-card::before {
    content: "";
    position: absolute;
    left: 0.75rem;
    top: 0.75rem;
    width: 1.55rem;
    height: 1.55rem;
    border-radius: 0.4rem;
    background: #dbeafe;
}

.rf-work-card::after {
    content: "";
    position: absolute;
    left: 2.7rem;
    right: 0.75rem;
    top: 0.88rem;
    height: 2.05rem;
    border-radius: 0.25rem;
    background:
        linear-gradient(#94a3b8, #94a3b8) 0 0 / 100% 0.25rem no-repeat,
        linear-gradient(#cbd5e1, #cbd5e1) 0 0.72rem / 82% 0.22rem no-repeat,
        linear-gradient(#cbd5e1, #cbd5e1) 0 1.38rem / 64% 0.22rem no-repeat;
}

.rf-work-card.card-a {
    left: 41%;
    top: 13.5rem;
}

.rf-work-card.card-b {
    left: 50%;
    top: 17.1rem;
    animation-delay: -1.7s;
}

.rf-work-card.card-c {
    left: 59%;
    top: 12.6rem;
    animation-delay: -3.1s;
}

.rf-ai-node {
    position: absolute;
    right: 10%;
    bottom: 7.4rem;
    width: 8.8rem;
    height: 8.8rem;
    border-radius: 50%;
    background: linear-gradient(135deg, #2563eb, #14b8a6);
    box-shadow: 0 18px 40px rgba(37, 99, 235, 0.20);
    animation: rfPulseNode 4.5s ease-in-out infinite;
    z-index: 4;
}

.rf-ai-node::before {
    content: "AI";
    position: absolute;
    inset: 1.45rem;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.92);
    color: #1e3a8a;
    font-weight: 840;
    font-size: 1.45rem;
}

.rf-flow-line {
    position: absolute;
    left: 36%;
    right: 19%;
    bottom: 12rem;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.48), transparent);
    z-index: 3;
}

.rf-flow-line::after {
    content: "";
    position: absolute;
    top: -0.32rem;
    left: 10%;
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    background: #2563eb;
    box-shadow: 0 0 18px rgba(37, 99, 235, 0.55);
    animation: rfTravel 3.8s linear infinite;
}

.rf-work-note {
    position: relative;
    max-width: none;
    z-index: 7;
    margin: 1.35rem 1.65rem 0;
    padding: 1rem 1.1rem;
    border-radius: 0.5rem;
    background: rgba(255, 255, 255, 0.76);
    border: 1px solid rgba(203, 213, 225, 0.55);
    box-shadow: 0 14px 32px rgba(30, 41, 59, 0.07);
    backdrop-filter: blur(10px);
}

.rf-testin-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: #0f5ccc;
    font-size: 0.84rem;
    font-weight: 800;
    margin-bottom: 0.65rem;
}

.rf-testin-mark {
    width: 1.1rem;
    height: 1.1rem;
    border-radius: 0.28rem;
    background: linear-gradient(135deg, #0f69ff, #16c7c8);
    box-shadow: 0 8px 18px rgba(15, 105, 255, 0.20);
}

.rf-work-note-title {
    color: #1e293b;
    font-size: 1.28rem;
    font-weight: 790;
    line-height: 1.25;
}

.rf-work-note-copy {
    color: #64748b;
    font-size: 0.95rem;
    line-height: 1.7;
    margin-top: 0.62rem;
}

.rf-testin-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.8rem;
}

.rf-testin-tags span {
    color: #1d4ed8;
    font-size: 0.76rem;
    font-weight: 720;
    padding: 0.24rem 0.52rem;
    border-radius: 999px;
    background: rgba(219, 234, 254, 0.86);
    border: 1px solid rgba(147, 197, 253, 0.40);
}

.rf-test-cloud {
    position: absolute;
    right: 23%;
    top: 10.8rem;
    width: 10.5rem;
    height: 5.1rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(147, 197, 253, 0.42);
    box-shadow: 0 18px 36px rgba(37, 99, 235, 0.08);
    z-index: 3;
}

.rf-test-cloud::before,
.rf-test-cloud::after {
    content: "";
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(147, 197, 253, 0.30);
}

.rf-test-cloud::before {
    width: 4rem;
    height: 4rem;
    left: 1.1rem;
    top: -1.25rem;
}

.rf-test-cloud::after {
    width: 4.8rem;
    height: 4.8rem;
    right: 1rem;
    top: -1.75rem;
}

.rf-device-stack {
    position: absolute;
    right: 25.6%;
    top: 11.4rem;
    display: flex;
    gap: 0.45rem;
    align-items: flex-end;
    z-index: 4;
}

.rf-device {
    width: 2.1rem;
    height: 3.6rem;
    border-radius: 0.42rem;
    background: linear-gradient(180deg, #e0f2fe, #ffffff);
    border: 1px solid rgba(37, 99, 235, 0.20);
    box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.rf-device:nth-child(2) {
    height: 4.35rem;
}

.rf-device:nth-child(3) {
    height: 3.05rem;
}

.rf-quality-check {
    position: absolute;
    right: 18%;
    top: 13.5rem;
    width: 2.8rem;
    height: 2.8rem;
    border-radius: 50%;
    background: linear-gradient(135deg, #22c55e, #14b8a6);
    box-shadow: 0 10px 24px rgba(20, 184, 166, 0.18);
    z-index: 5;
    animation: rfPulseNode 4.8s ease-in-out infinite;
}

.rf-quality-check::before {
    content: "";
    position: absolute;
    left: 0.82rem;
    top: 0.78rem;
    width: 1rem;
    height: 0.55rem;
    border-left: 0.22rem solid #fff;
    border-bottom: 0.22rem solid #fff;
    transform: rotate(-45deg);
}

@keyframes rfSun {
    0%, 100% { transform: translateY(0); opacity: 0.92; }
    50% { transform: translateY(-0.55rem); opacity: 1; }
}

@keyframes rfFloatCard {
    0%, 100% { transform: translateY(0) rotate(-1deg); }
    50% { transform: translateY(-0.7rem) rotate(1deg); }
}

@keyframes rfPulseNode {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.035); }
}

@keyframes rfTravel {
    from { transform: translateX(0); opacity: 0; }
    12% { opacity: 1; }
    82% { opacity: 1; }
    to { transform: translateX(39vw); opacity: 0; }
}

[data-testid="stFileUploader"] button,
.stButton > button,
[data-testid="stLinkButton"] a {
    border-radius: 0.5rem !important;
    border: 1px solid var(--rf-border-strong) !important;
    font-weight: 650 !important;
    min-height: 2.45rem;
}

.stButton > button:hover,
[data-testid="stLinkButton"] a:hover {
    border-color: var(--rf-accent) !important;
    color: var(--rf-accent-dark) !important;
}

.stButton > button[kind="primary"] {
    background: var(--rf-accent) !important;
    border-color: var(--rf-accent) !important;
    color: #fff !important;
    box-shadow: 0 9px 18px rgba(255, 79, 79, 0.22);
}

.stButton > button[kind="primary"]:hover {
    background: var(--rf-accent-dark) !important;
    border-color: var(--rf-accent-dark) !important;
    color: #fff !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--rf-border) !important;
    border-radius: 0.65rem !important;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 14px 34px rgba(31, 41, 55, 0.06);
    overflow: hidden;
}

[data-testid="stExpander"] details > summary {
    background: var(--rf-panel-soft);
    border-bottom: 1px solid var(--rf-border);
}

[data-testid="stForm"] {
    border: 0;
    padding: 0.2rem 0 0;
}

[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="base-input"],
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    border-radius: 0.5rem !important;
    background: #f3f6fb !important;
    border-color: transparent !important;
}

[data-baseweb="input"] > div:focus-within,
[data-baseweb="select"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within {
    background: #fff !important;
    border-color: var(--rf-blue) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
}

[data-baseweb="tag"] {
    border-radius: 0.42rem !important;
    background: var(--rf-accent) !important;
    color: #fff !important;
}

[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, var(--rf-blue), #14b8a6) !important;
}

[data-testid="stAlert"] {
    border-radius: 0.65rem;
    border: 1px solid rgba(31, 41, 55, 0.06);
}

[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid var(--rf-border);
    border-radius: 0.65rem;
    padding: 1rem 1.1rem;
    box-shadow: 0 10px 26px rgba(31, 41, 55, 0.05);
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--rf-border);
    border-radius: 0.65rem;
    overflow: hidden;
    box-shadow: 0 10px 24px rgba(31, 41, 55, 0.04);
}

textarea {
    line-height: 1.55 !important;
}

@media (max-width: 900px) {
    .block-container {
        padding-top: 1.35rem;
    }

    h1 {
        font-size: 2rem !important;
    }

    .rf-work-visual {
        min-height: 520px;
    }

    .rf-work-note {
        margin: 1rem;
        left: auto;
        right: auto;
        top: auto;
        max-width: none;
    }

    .rf-work-window {
        width: 70%;
        height: 36%;
        right: 1.2rem;
        top: 16rem;
    }

    .rf-work-laptop {
        left: 1.6rem;
        width: 14rem;
        bottom: 6.1rem;
    }

    .rf-work-person,
    .rf-work-card.card-c {
        display: none;
    }

    .rf-work-card.card-a {
        left: 50%;
        top: 18rem;
    }

    .rf-work-card.card-b {
        left: 58%;
        top: 21.5rem;
    }

    .rf-ai-node {
        right: 1.6rem;
        width: 6.5rem;
        height: 6.5rem;
    }

    .rf-test-cloud,
    .rf-device-stack,
    .rf-quality-check {
        display: none;
    }
}
</style>
"""

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


def apply_global_styles() -> None:
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="rf-sidebar-brand">
            <div class="rf-brand-mark">RF</div>
            <div>
                <div class="rf-brand-title">RecruitFlow AI</div>
                <div class="rf-brand-subtitle">招聘流程提效助手</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    module = st.sidebar.radio(
        "功能模块",
        MODULE_OPTIONS,
        format_func=lambda value: f"{value} ｜ {MODULE_PAGES[value]}",
    )
    return MODULE_PAGES[module]


def render_upload_work_visual() -> None:
    st.markdown(
        """
        <div class="rf-work-visual" aria-hidden="true">
            <div class="rf-work-note">
                <div class="rf-testin-badge"><span class="rf-testin-mark"></span>Testin云测 · 助力产业智能化</div>
                <div class="rf-work-note-title">把质量意识带进招聘流程，把合适的人更快带到团队面前</div>
                <div class="rf-work-note-copy">
                    清晨的工位、翻开的简历、云端流转的候选人信息，下一段共同工作的故事正在靠近。
                </div>
                <div class="rf-testin-tags">
                    <span>云测试</span>
                    <span>AI 数据</span>
                    <span>安全服务</span>
                </div>
            </div>
            <div class="rf-work-window"></div>
            <div class="rf-work-sun"></div>
            <div class="rf-test-cloud"></div>
            <div class="rf-device-stack">
                <div class="rf-device"></div>
                <div class="rf-device"></div>
                <div class="rf-device"></div>
            </div>
            <div class="rf-quality-check"></div>
            <div class="rf-flow-line"></div>
            <div class="rf-work-laptop"></div>
            <div class="rf-work-person"></div>
            <div class="rf-work-card card-a"></div>
            <div class="rf-work-card card-b"></div>
            <div class="rf-work-card card-c"></div>
            <div class="rf-ai-node"></div>
            <div class="rf-work-desk"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def join_people(selected: list[str]) -> str:
    return "、".join(unique_people(selected))


def people_multiselect(
    label: str,
    options: list[str],
    current_value: str | None,
    key_prefix: str,
) -> str:
    current_people = split_people(current_value)
    selectable_options = unique_people([*options, *current_people])
    selected = st.multiselect(
        label,
        selectable_options,
        default=current_people,
        key=f"{key_prefix}_select",
    )
    return join_people(selected)


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
                position = st.selectbox(
                    "应聘岗位",
                    POSITION_OPTIONS,
                    index=0,
                    key=f"{prefix}_position",
                )
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
                            "next_action": None,
                            "hr_decision": hr_decision,
                            "notes": none_if_blank(notes),
                        },
                    }
                    response = post_json("/api/candidates/confirm", payload)
                    if response:
                        st.session_state[f"save_response_{result_key}"] = response
                        if response.get("updated_existing_application"):
                            st.success("已更新已有候选人记录，并同步腾讯文档。")
                        else:
                            st.success("保存成功，并同步腾讯文档。")
                        if response.get("matched_existing"):
                            st.info(f"已关联已有候选人，匹配方式：{response.get('match_type')}")
                        if response.get("tencent_docs_url"):
                            st.link_button("打开腾讯文档表格", response["tencent_docs_url"])

        saved_response = st.session_state.get(f"save_response_{result_key}")
        if saved_response:
            if saved_response.get("updated_existing_application"):
                st.info("已更新已有候选人记录。")
            else:
                st.info("已保存候选人记录。")
            if saved_response.get("tencent_docs_url"):
                st.link_button("打开腾讯文档表格", saved_response["tencent_docs_url"])


def page_upload_resume() -> None:
    st.title("上传简历")
    uploaded_files = st.file_uploader(
        "上传候选人 PDF 简历，可一次选择多份",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        render_upload_work_visual()
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
                "next_action": None,
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
    apply_global_styles()
    page = render_sidebar()

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
