# RecruitFlow AI｜招聘流程提效助手

这是一个招聘流程提效 AI Demo。HR 上传简历 PDF 后，系统自动解析候选人信息，HR 确认招聘流程字段后写入数据库并同步腾讯文档，同时根据面试时间通过企业微信群机器人发送提醒。

## 架构图

面向 HR 的通俗版架构图见：[RecruitFlow AI 架构图](docs/architecture.md)。

## 功能

- 一次上传一份或多份文本型 PDF 简历并自动提取文本
- 调用 OpenAI-compatible API 解析候选人信息
- 未配置 LLM 时使用本地规则解析兜底，方便演示流程
- HR 确认候选人字段和招聘流程字段
- SQLite 保存候选人和投递记录
- 按手机号、邮箱、姓名 + 学校 + 专业做简单去重
- 使用腾讯文档 OpenAPI 创建在线表格并写入数据，未配置时回落到本地 CSV mock
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
LLM_PROVIDER=openai_compatible
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
WECOM_WEBHOOK_URL=
TENCENT_DOCS_CLIENT_ID=
TENCENT_DOCS_ACCESS_TOKEN=
TENCENT_DOCS_OPEN_ID=
TENCENT_DOCS_FILE_ID=
TENCENT_DOCS_SHEET_ID=
TENCENT_DOCS_TITLE=RecruitFlow AI 候选人台账
TENCENT_DOCS_URL=
DAILY_SUMMARY_HOUR=9
DAILY_SUMMARY_MINUTE=0
REMINDER_SCAN_INTERVAL_MINUTES=5
DATABASE_URL=sqlite:///./backend/data/recruit.db
APP_TIMEZONE=Asia/Shanghai
```

不要把真实 API Key、企业微信群机器人 Webhook 提交到代码仓库。

## 腾讯文档写入

如果只配置本地开发环境，可以不填腾讯文档参数，系统会写入 `backend/data/tencent_docs_mock.csv`。

如果已经从腾讯文档开放平台拿到 `client_id`、`access_token`、`open_id`，按下面方式填入 `.env`：

```env
TENCENT_DOCS_CLIENT_ID=你的 client_id
TENCENT_DOCS_ACCESS_TOKEN=你的 access_token
TENCENT_DOCS_OPEN_ID=你的 open_id
```

启动后第一次保存候选人时，系统会自动创建一个在线表格，写入表头，并把候选人投递记录写入第二行开始的数据区。创建出来的 `book_id`、`sheet_id`、腾讯文档 URL 和 `application_id -> 行号` 映射会保存在本地 `backend/data/tencent_docs_state.json`，该文件已加入 `.gitignore`。保存成功后前端会展示腾讯文档链接，企业微信群提醒也会附带这条台账链接。

如果你希望写入已有腾讯文档表格，可以额外配置：

```env
TENCENT_DOCS_FILE_ID=300000000$xxxxxxxxxxxx
TENCENT_DOCS_SHEET_ID=BB0000
TENCENT_DOCS_URL=https://docs.qq.com/sheet/xxxxxxxx
```

`access_token` 会过期；当前 MVP 直接使用你填入的 token，不包含 OAuth refresh token 自动刷新流程。

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

腾讯文档真实 API 已支持使用 `client_id`、`access_token`、`open_id` 创建在线表格并写入候选人数据；未配置时默认使用 `backend/data/tencent_docs_mock.csv` 模拟。

企业微信不负责读取群消息，本系统只使用企业微信群机器人 Webhook 做消息推送。
