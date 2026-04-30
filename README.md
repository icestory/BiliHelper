# BiliHelper

B 站视频内容解析、总结与问答工具。输入 B 站链接，自动获取字幕/语音识别，调用大模型生成摘要、章节划分，支持问答和 Markdown 导出。

## 功能

- **B 站链接解析** — 支持 BV/AV/短链/分P 链接，自动获取视频元信息
- **字幕获取** — 优先使用 UP 主上传字幕、AI 字幕，无字幕时自动 ASR 兜底
- **LLM 总结** — 调用大模型生成视频摘要、详细总结、关键要点和章节划分
- **分 P 支持** — 多 P 视频独立分析 + 全视频聚合总结
- **视频问答** — 基于文案内容的上下文问答，回答带时间引用
- **Markdown 导出** — 一键导出完整分析结果（含文案、总结、章节、问答记录）
- **用户管理** — 注册/登录，API Key 加密存储，多供应商支持

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | Python 3.12+ / FastAPI |
| 数据校验 | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| 数据库迁移 | Alembic |
| 数据库 | PostgreSQL（开发可用 SQLite） |
| 任务队列 | Celery + Redis |
| 前端 | React + TypeScript + Vite |
| 前端路由 | React Router |
| LLM 调用 | OpenAI 兼容接口（支持 OpenAI / DeepSeek / Qwen / Ollama 等） |
| ASR | OpenAI Whisper / faster-whisper（本地） |
| 音频处理 | yt-dlp + FFmpeg |
| 部署 | Docker Compose / Nginx 反向代理 |

## 架构

```
浏览器 → Nginx(:80)
            ├─ /          → React SPA 静态文件
            └─ /api/*     → FastAPI(:8000)
                              ├─ 认证/配置/CRUD
                              └─ Celery Worker(异步)
                                   ├─ B站适配器(字幕/元信息)
                                   ├─ ASR Provider(音频提取→语音识别)
                                   └─ LLM Provider(总结/章节/问答)
            ↑                    ↑              ↑
        PostgreSQL            Redis         FFmpeg
```

**核心处理链路：**

```
用户提交链接 → 解析视频/分P → 创建分析任务 → Celery Worker
  → 获取字幕（无字幕→提取音频→ASR）
  → Transcript 段落保存 → Chunk 检索分块
  → LLM 生成总结+章节 → 全视频聚合总结
  → 前端轮询完成 → 查看/导出/问答
```

## 快速开始

### Docker 部署（推荐）

```bash
git clone https://github.com/icestory/BiliHelper.git
cd BiliHelper
cp .env.example .env
# 编辑 .env，填入 APP_SECRET_KEY 和 CREDENTIAL_ENCRYPTION_KEY
docker compose up -d
```

浏览器打开 `http://你的服务器IP`。

### 本地开发

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env  # 编辑 DATABASE_URL 和 REDIS_URL 指向本地
alembic upgrade head
uvicorn app.main:app --reload

# 前端（新终端）
cd web
npm install
npm run dev

# Worker（新终端）
cd backend && source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info
```

本地开发时 `.env` 中将 `DATABASE_URL` 和 `REDIS_URL` 切换为 localhost 版本（模板中已注释）。

> 详细部署指南见 [doc/deploy-guide.md](doc/deploy-guide.md)

## 项目结构

```
BiliHelper/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/                  # 路由层 (auth, videos, analysis_tasks, qa, exports)
│   │   ├── core/                 # 配置、数据库、安全、依赖注入
│   │   ├── models/               # SQLAlchemy ORM (15张表)
│   │   ├── schemas/              # Pydantic 请求/响应模型
│   │   ├── services/             # 业务逻辑 (auth, video, analysis, qa, export, transcript)
│   │   ├── repositories/         # 数据访问层
│   │   ├── integrations/
│   │   │   ├── bilibili/         # B站适配器 (resolver, metadata, subtitles, audio)
│   │   │   ├── llm/              # LLM Provider (OpenAI 兼容)
│   │   │   └── asr/              # ASR Provider (OpenAI Whisper + faster-whisper)
│   │   ├── workers/              # Celery 异步任务
│   │   ├── prompts/              # LLM Prompt 模板（版本化）
│   │   └── exporters/            # Markdown 导出
│   ├── migrations/               # Alembic 迁移
│   ├── tests/
│   └── pyproject.toml
├── web/
│   ├── src/
│   │   ├── api/                  # API 客户端 (fetch + token 自动刷新)
│   │   ├── components/           # 可复用组件 (NavBar, ChapterList, TranscriptView...)
│   │   ├── pages/                # 页面 (Login, History, VideoDetail, QAPage, Settings...)
│   │   ├── routes/               # React Router 配置
│   │   └── types/                # TypeScript 类型定义
│   └── vite.config.ts
├── docker/                       # Nginx 配置
├── doc/                          # 产品/技术/部署文档
├── docker-compose.yml
└── .env.example
```

## API 概览

| 端点 | 说明 |
|------|------|
| `POST /api/auth/register` | 用户注册 |
| `POST /api/auth/login` | 用户登录 |
| `GET /api/auth/me` | 当前用户信息 |
| `GET/POST/PATCH/DELETE /api/llm-configs` | 大模型配置 CRUD |
| `POST /api/videos/parse` | 解析 B 站链接 |
| `GET /api/videos/history` | 历史记录（分页/搜索） |
| `GET /api/videos/:id` | 视频详情 + 分 P 列表 |
| `POST /api/analysis-tasks` | 创建分析任务 |
| `GET /api/analysis-tasks/:id` | 查询任务状态（前端轮询） |
| `POST /api/analysis-tasks/:id/retry` | 重试失败任务 |
| `GET /api/parts/:id/analysis` | 分 P 分析详情（文案+总结+章节） |
| `POST /api/qa-sessions` | 创建问答会话 |
| `POST /api/qa-sessions/:id/messages` | 发送问题（含引用） |
| `GET /api/exports/videos/:id.md` | 导出全视频 Markdown |
| `GET /api/exports/parts/:id.md` | 导出单 P Markdown |

## 配置

通过 `.env` 文件配置，主要变量：

| 变量 | 说明 |
|------|------|
| `APP_SECRET_KEY` | JWT 签名密钥 |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet 密钥（加密用户 API Key） |
| `DATABASE_URL` | 数据库连接串 |
| `REDIS_URL` | Redis 连接串 |
| `API_BASE_URL` / `WEB_BASE_URL` | 服务外网地址 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期（默认 30 分钟） |
| `MAX_VIDEO_DURATION_SECONDS` | 单视频最大时长限制（默认 2 小时） |

## 设计原则

- **自带 API Key** — 用户自行配置 LLM API Key，后端加密存储，不依赖单一供应商
- **字幕优先、ASR 兜底** — 优先 B 站字幕，无字幕时自动提取音频转文字
- **Prompt 版本化** — 所有 LLM Prompt 模板带版本号，结果可追溯
- **临时文件即时清理** — 音频提取仅用于 ASR，任务完成后自动删除
- **瘦客户端** — 所有重逻辑在后端，Web 仅做 UI 和状态展示

## License

MIT
