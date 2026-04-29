# BiliHelper 开发计划

生成日期：2026-04-29

## 开发原则

- **后端优先**：Web 和 Android 都是瘦客户端，一切能力以后端 API 为基础
- **每步可验证**：每个阶段产出可独立运行、可测试的增量
- **增量交付**：小步提交，每步编译通过 + 测试通过
- **M0 最重要**：地基打好，后续都是添砖加瓦

---

## M0：基础工程

**目标**：搭建完整工程骨架，用户可注册登录，Docker 一键启动

### 后端

- [x] FastAPI 项目结构（`backend/app/` 目录树、`main.py` 入口、配置管理）
- [x] SQLAlchemy ORM 全部数据模型（users / api_credentials / bilibili_credentials / videos / video_parts / analysis_tasks / part_analysis_tasks / transcript_segments / transcript_chunks / part_summaries / chapters / video_summaries / qa_sessions / qa_messages / export_records）
- [x] Alembic 初始迁移
- [x] 用户注册/登录（Argon2id 密码哈希、JWT access token + refresh token）
- [x] API Key 加密存储（AES-GCM / Fernet，主密钥环境变量注入）
- [x] `GET /api/auth/me` 当前用户接口

### Web

- [x] React + TypeScript + Vite 项目初始化
- [x] React Router 路由配置
- [x] 登录/注册页面
- [x] API 客户端封装（TanStack Query）

### 部署

- [x] Docker Compose（api / worker / redis / postgres / nginx / web）
- [x] `.env.example` 环境变量模板
- [x] Nginx 反向代理配置

### 测试

- [x] 用户注册/登录集成测试
- [x] API Key CRUD + 加密测试

---

## M1：视频解析与历史

**目标**：输入 B 站链接，解析元信息和分 P 列表，保存和查看历史

### 后端

- [x] BilibiliResolver — 链接归一化、BV/AV 提取、短链展开
- [x] BilibiliMetadataProvider — 视频和分 P 元信息获取
- [x] `POST /api/videos/parse` 接口
- [x] 视频和分 P 信息写入数据库
- [x] `GET /api/videos/history` 历史列表（分页、搜索、筛选）
- [x] `GET /api/videos/{video_id}` 视频详情
- [x] `DELETE /api/videos/{video_id}/history` 删除历史

### Web

- [x] LinkInput 组件 — 输入链接并提交解析
- [x] VideoPreview 组件 — 展示视频信息和分 P 列表
- [x] HistoryList 页面 — 历史记录搜索和筛选

### 测试

- [x] 链接解析单元测试（BV/AV/短链/带 p 参数/移动端分享文本）
- [x] 历史记录权限隔离测试

---

## M2：字幕、文案与总结（核心链路）

**目标**：异步获取字幕、生成文案分段、LLM 总结和章节划分

### 后端

- [x] BilibiliSubtitleProvider — 字幕适配层（UP 主字幕 > 自动字幕 > AI 字幕）
- [x] 字幕 JSON 标准化（统一 start_time / end_time / text 格式）
- [x] Celery Worker 搭建（`celery_app.py`、任务路由、状态更新）
- [x] `POST /api/analysis-tasks` 创建分析任务
- [x] `GET /api/analysis-tasks/{id}` 查询任务状态
- [x] LLM Provider 抽象层（OpenAI 兼容接口）
- [x] 总结 + 章节 Prompt（`prompts/summary_chapters_v1.txt`）
- [x] LLM JSON 结构化输出校验（Pydantic 二次校验 + 一次自动修复重试）
- [x] 长文案 chunk 切分 → 局部摘要 → 合并策略
- [x] 任务状态机（waiting → running → completed / failed）

### Web

- [x] PartSelector 组件 — 选择分析范围
- [x] TaskProgress 页面 — 轮询展示任务状态和进度
- [x] PartAnalysisView 页面 — 单 P 文案、总结、章节
- [x] ChapterList 组件 — 可点击章节时间点
- [x] TranscriptView 组件 — 带时间戳文案展示

### 测试

- [x] 字幕标准化单元测试
- [x] LLM JSON 校验单元测试
- [x] 任务状态机流转测试
- [x] 长文案切分单元测试

---

## M3：ASR 兜底

**目标**：无字幕时自动提取音频并语音识别

### 后端

- [x] AudioExtractor — yt-dlp + FFmpeg 提取临时音频
- [x] 音频格式转换（mono wav/mp3）
- [x] ASR Provider 抽象层
- [x] OpenAI Speech-to-Text Provider（云端）
- [x] faster-whisper Provider（本地，可选）
- [x] 音频切片（处理文件大小限制）
- [x] 分片结果合并 + 时间偏移修正
- [x] 临时音频清理（任务完成/失败后自动删除）

### Web

- [x] 分析进度中区分"获取字幕"和"语音识别"状态

### 测试

- [x] 音频切片/合并逻辑单元测试
- [x] ASR 结果标准化测试

---

## M4：分 P 完整链路

**目标**：多 P 视频完整支持，部分选择、独立任务、全视频总结

### 后端

- [x] 分 P 选择支持（全部 / 当前 P / 自定义选择）
- [x] 每 P 独立 `part_analysis_task`
- [x] Worker 并发/串行处理各 P
- [x] 全视频总结生成（基于各 P 总结聚合）
- [x] `partial_failed` 状态支持
- [x] `POST /api/analysis-tasks/{id}/retry` 失败重试
- [x] `POST /api/parts/{part_id}/reanalyze` 单 P 重新分析

### Web

- [x] 分 P 选择 UI（复选框 + 全选）
- [x] 多 P 任务进度展示（各 P 独立状态）
- [x] 全视频总结展示
- [x] 重试按钮

### 测试

- [x] 分 P 多任务并发测试
- [x] partial_failed 状态流转测试
- [x] 单 P 重试测试

---

## M5：问答与导出

**目标**：基于视频内容的问答和 Markdown 导出

### 后端

- [ ] Transcript chunk 聚合（按 token 数切分，存入 `transcript_chunks`）
- [ ] 问答检索（MVP: PostgreSQL 全文检索 / 关键词匹配）
- [ ] QA Prompt 构造（总结 + 章节 + 相关 chunks + 引用要求）
- [ ] `POST /api/videos/{video_id}/qa-sessions` 创建问答会话
- [ ] `POST /api/qa-sessions/{session_id}/messages` 发送问题
- [ ] `GET /api/qa-sessions/{session_id}/messages` 获取历史消息
- [ ] Markdown 导出模板（全视频 / 单 P）
- [ ] `GET /api/exports/videos/{video_id}.md` 导出接口
- [ ] `GET /api/exports/parts/{part_id}.md` 导出接口

### Web

- [ ] QAView 页面 — 聊天式问答界面
- [ ] 引用时间点点击跳转（定位到 transcript + 打开 B 站链接）
- [ ] ExportMenu 组件 — 导出选项（含/不含文案、章节、问答）
- [ ] Markdown 文件下载

### 测试

- [ ] Transcript chunk 切分单元测试
- [ ] 关键词检索测试
- [ ] Markdown 模板渲染测试
- [ ] 问答引用格式测试

---

## M6：Android

**目标**：Android App 覆盖核心移动场景

### 工程

- [ ] Kotlin + Jetpack Compose 项目初始化
- [ ] Retrofit + OkHttp 网络层
- [ ] EncryptedSharedPreferences token 存储

### 功能

- [ ] LoginScreen — 登录页
- [ ] HomeScreen — 首页（入口汇总）
- [ ] 手动输入 B 站链接
- [ ] 接收 B 站分享（`ACTION_SEND`，`text/plain`）
- [ ] SharedLinkConfirmScreen — 分享链接确认页
- [ ] VideoParseScreen — 视频解析确认
- [ ] TaskProgressScreen — 任务进度查看
- [ ] HistoryScreen — 历史记录
- [ ] VideoDetailScreen / PartDetailScreen — 视频/分 P 详情
- [ ] QAScreen — 基础问答
- [ ] Markdown 分享（系统 Share Sheet）

### 测试

- [ ] 分享 Intent 解析测试
- [ ] 登录状态恢复测试

---

## 后续增强（M7+）

MVP 稳定后再考虑：

- [ ] pgvector 语义检索（替代关键词检索）
- [ ] SSE 任务进度推送（替代轮询）
- [ ] 多模型配置策略（不同任务用不同模型）
- [ ] B 站 Cookie UI 配置
- [ ] 章节手动修正
- [ ] Obsidian/Notion 导出
- [ ] 批量视频分析
- [ ] Android 离线缓存
- [ ] 本地-only 模式（无外部 LLM 依赖时使用 Ollama）

---

## 里程碑总结

| 里程碑 | 核心交付 | 依赖 |
|--------|---------|------|
| M0 | 工程骨架 + 用户认证 + Docker | 无 |
| M1 | 链接解析 + 历史记录 | M0 |
| M2 | 字幕获取 + LLM 总结（核心链路） | M1 |
| M3 | ASR 兜底 | M2 |
| M4 | 分 P 完整支持 | M2 |
| M5 | 问答 + Markdown 导出 | M4 |
| M6 | Android App | M5 |
