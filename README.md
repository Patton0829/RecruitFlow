# RecruitFlow AI｜招聘流程提效助手

这是一个招聘流程提效 AI Demo。HR 上传简历 PDF 后，系统自动解析候选人信息，HR 确认招聘流程字段后写入数据库并同步腾讯文档，同时根据面试时间通过企业微信群机器人发送提醒。

## 功能

- 一次上传一份或多份文本型 PDF 简历并自动提取文本
- 调用 OpenAI-compatible API 解析候选人信息
- 未配置 LLM 时使用本地规则解析兜底，方便演示流程
- HR 确认候选人字段和招聘流程字段
- SQLite 保存候选人和投递记录
- 按手机号、邮箱、姓名 + 学校 + 专业做简单去重
- 使用本地 CSV mock 腾讯文档同步
- 展示候选人列表和招聘看板
- 企业微信群机器人提醒，未配置 Webhook 时打印到后端控制台
- APScheduler 自动发送每日面试汇总和面试前 1 小时提醒

## 运行方式

```bash
pip install -r requirements.txt
cp .env.example .env
```

启动后端：

```bash
uvicorn backend.main:app --reload --port 8000
```

启动前端：

```bash
streamlit run frontend/app.py
```

打开 Streamlit 页面后，默认连接 `http://localhost:8000`。如需修改后端地址：

```bash
API_BASE_URL=http://localhost:8000 streamlit run frontend/app.py
```

## 环境变量

`.env` 中可以按需配置：

```env
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
WECOM_WEBHOOK_URL=
TENCENT_DOCS_APP_ID=
TENCENT_DOCS_APP_SECRET=
TENCENT_DOCS_FILE_ID=
TENCENT_DOCS_SHEET_ID=
DAILY_SUMMARY_HOUR=9
DAILY_SUMMARY_MINUTE=0
REMINDER_SCAN_INTERVAL_MINUTES=5
DATABASE_URL=sqlite:///./backend/data/recruit.db
APP_TIMEZONE=Asia/Shanghai
```

不要把真实 API Key、企业微信群机器人 Webhook 提交到代码仓库。

## Demo 流程

1. 打开 Streamlit 页面。
2. 上传一份或多份文本型 PDF 简历。
3. 等待系统自动解析并查看解析进度。
4. 检查并修改每份简历的解析结果。
5. 填写岗位、来源、阶段、面试时间、面试官、负责 HR。
6. 点击保存。
7. 在候选人列表查看记录。
8. 在招聘看板查看统计。
9. 在提醒测试页手动触发今日面试汇总或 1 小时提醒。
10. 如果配置了企业微信群机器人 Webhook，群里会收到提醒；否则控制台打印提醒内容。

## API

- `POST /api/resumes/parse`：上传并解析简历 PDF
- `POST /api/candidates/confirm`：确认并保存候选人和招聘流程
- `GET /api/candidates`：查询候选人列表，支持阶段、状态、岗位、来源、面试时间筛选
- `PATCH /api/applications/{application_id}`：更新招聘流程
- `GET /api/dashboard/summary`：招聘看板数据
- `POST /api/reminders/send-daily-summary`：手动触发今日面试汇总
- `POST /api/reminders/scan-upcoming`：手动扫描面试前 1 小时提醒
- `POST /api/reminders/test-wecom`：发送企业微信群机器人测试消息

## MVP 边界

当前版本支持文本型 PDF 简历解析。扫描版 PDF 暂不支持 OCR。

腾讯文档真实 API 对接保留 `TencentDocsClient` 接口，默认使用 `backend/data/tencent_docs_mock.csv` 模拟。

企业微信不负责读取群消息，本系统只使用企业微信群机器人 Webhook 做消息推送。
