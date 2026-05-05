# BiliHelper 全量代码审查报告

审查日期：2026-05-05  
审查范围：`backend/`、`web/`、`docker-compose.yml`、Dockerfile、Alembic 迁移、配置与文档入口  
审查方式：静态代码审查 + 可用命令验证

## Critical/High 修复记录

修复日期：2026-05-05

- 已修复 QA 会话列表 `QASession` 未导入导致的运行时崩溃。
- 已修复 Docker worker 启动命令，worker 现在复用镜像 entrypoint，并等待 API 健康后启动。
- 已补充 `yt-dlp` 依赖并修复音频提取异常清理，避免真实错误被 `UnboundLocalError` 掩盖。
- 已修复 B 站 `published_at` 写库类型，元信息层返回 `datetime` 而不是 ISO 字符串。
- 已新增用户分析结果归属字段和迁移，文案、chunk、摘要、章节、全视频总结按当前用户任务读取，避免跨用户覆盖/泄露。
- 已为视频详情、全视频总结、导出、QA 创建和 QA 上下文补充当前用户访问校验。
- 已对生产环境自定义 LLM/ASR Base URL 增加 SSRF 防护，禁止内网、本机、非 HTTPS 和无法解析域名。
- 已移除容器启动时 `alembic revision --autogenerate`，生产容器只执行已提交迁移。
- 已将 refresh token 改为带 `jti` 的会话化轮换机制，并新增 logout 撤销能力。

## 验证结果

- `python3 -m compileall backend/app backend/migrations`：通过，未发现 Python 语法错误。
- `git diff --check`：通过，未发现空白错误。
- `cd backend && .venv/bin/python -m ruff check app`：通过。
- `cd web && npm run build`：通过。
- `cd web && npm run lint`：已可执行，但失败于现有 React hooks 规则问题：5 errors、2 warnings。
- `cd backend && .venv/bin/python -m pytest`：已可执行，当前收集到 0 个测试用例。

## 严重问题（Critical）

### 1. QA 会话列表接口运行时必崩

`backend/app/api/qa.py:56-58` 在 `list_sessions()` 中直接使用 `QASession`，但该名称没有在模块级导入；`QASession` 只在 `create_session()` 内部局部导入（`backend/app/api/qa.py:83`）。访问 `GET /api/videos/{video_id}/qa-sessions` 会触发 `NameError`，前端 `QAPage` 会收到非 2xx 并静默显示空会话。

建议：在文件顶部导入 `from app.models.qa import QASession`，并为该接口补测试。

### 2. Docker worker 启动命令可能直接失败

`backend/Dockerfile:21-22` 只对 `/docker-entrypoint.sh` 做了 `chmod +x`。但 `docker-compose.yml:37-40` 覆盖 worker entrypoint 后执行的是 `docker-entrypoint.sh celery ...`，没有使用 `/docker-entrypoint.sh` 或 `./docker-entrypoint.sh`。当前工作目录下的源文件副本不一定可执行，且当前目录通常不在 `PATH` 中，worker 容器可能 `command not found`。

建议：将 worker 命令改为 `/docker-entrypoint.sh celery -A app.workers.celery_app worker ...`，或不要覆盖 Dockerfile 的 `ENTRYPOINT`。

### 3. ASR 兜底路径缺少核心依赖且错误会被掩盖

音频提取依赖 `yt-dlp`（`backend/app/integrations/bilibili/audio.py:42-48`），但后端镜像只安装了 `ffmpeg`（`backend/Dockerfile:6-8`），Python 依赖中也没有 `yt-dlp`（`backend/requirements.txt:1-13`）。当 `subprocess.Popen()` 因找不到 `yt-dlp` 失败时，`except Exception` 块会访问尚未赋值的 `ytdlp_proc`（`backend/app/integrations/bilibili/audio.py:61-75`），把真实错误替换成 `UnboundLocalError`。

建议：安装 `yt-dlp`，初始化 `ytdlp_proc = None`，异常清理前判空，并记录 stderr 或错误日志。

### 4. B 站发布时间类型不匹配，解析视频可能写库失败

`Video.published_at` 是 `DateTime` 列（`backend/app/models/video.py:26`），但 B 站元数据解析返回 ISO 字符串（`backend/app/integrations/bilibili/metadata.py:28,76`），随后直接传给 ORM 写库（`backend/app/services/video_service.py:44,64`）。在 SQLite 或严格驱动下会报 `DateTime type only accepts Python datetime`，在 PostgreSQL 下也依赖隐式转换，不稳定。

建议：`metadata.py` 返回 `datetime | None`，只在响应层 `isoformat()`。

## 高严重性（High）

### 5. 多个读取/导出接口缺少所有权校验

`GET /api/videos/{video_id}` 已认证但没有按当前用户过滤，直接调用 `get_video_detail(video_id)`（`backend/app/api/videos.py:33-36`）。`GET /api/videos/{video_id}/summary` 只按 `video_id` 查询（`backend/app/api/videos.py:49-52`）。导出接口虽然注入了 `current_user`（`backend/app/api/exports.py:13-29,32-46`），但服务函数没有接收 `user_id`，且 `include_qa=true` 会导出该视频所有 QA 会话（`backend/app/services/export_service.py:107-123`）。

影响：任意登录用户只要猜到 `video_id` 或 `part_id`，就可能读取其他用户生成的总结、文案和问答记录。

建议：所有详情、总结、导出、QA 列表接口统一校验 `AnalysisTask.user_id` 或显式资源归属；导出 QA 时必须按 `QASession.user_id` 过滤。

### 6. 分析结果是全局共享并会被其他用户覆盖

`TranscriptSegment`、`TranscriptChunk`、`PartSummary`、`Chapter`、`VideoSummary` 都没有 `user_id` 或 `analysis_task_id` 归属字段（例如 `backend/app/models/transcript.py:8-33`、`backend/app/models/summary.py:14-53`）。Worker 保存结果时按 `video_part_id` 删除旧数据（`backend/app/workers/tasks/analyze_part.py:72-118`），会覆盖同一分 P 的所有历史结果。

影响：用户 B 重新分析同一公开视频会删除/替换用户 A 的文案、总结和章节；权限检查即使通过，也可能读到其他用户最后一次生成的内容。

建议：如果结果是用户私有数据，应把结果表关联到 `analysis_task_id` 或 `user_id`；如果要做全局缓存，应把用户私有的 QA、模型、prompt 和导出记录严格隔离。

### 7. QA 会话创建缺少视频和 part 范围校验

`QAService.create_session()` 直接保存传入的 `video_id`、`scope`、`part_ids`（`backend/app/services/qa_service.py:100-112`），没有检查视频是否存在、当前用户是否有访问权、`part_ids` 是否属于该视频。随后 `_build_context()` 会按这些 part id 查询总结和 transcript chunk。

建议：创建会话前校验视频归属和每个 part 的 `video_id`，并限制 `scope` 枚举值。

### 8. 用户可控 LLM Base URL 带来 SSRF 风险

凭据 schema 接受任意 `api_base_url`（`backend/app/schemas/credential.py:4-17`），后端会拼接并请求 `${base_url}/chat/completions`（`backend/app/integrations/llm/openai_compatible.py:26`）和 `${base_url}/audio/transcriptions`（`backend/app/integrations/asr/openai_asr.py:61`）。如果开放注册，攻击者可让服务器访问内网地址或云元数据地址。

建议：生产环境对 `api_base_url` 做 allowlist、禁止内网/本机/链路本地地址，或将自定义 provider 设为管理员能力。

### 9. 容器启动时自动生成迁移存在生产风险

`backend/docker-entrypoint.sh:12` 每次启动都会运行 `alembic revision --autogenerate`，并且 API 与 worker 都会执行同一个 entrypoint（`docker-compose.yml:12-40`）。这会在容器内生成不可审查的迁移文件，多个容器并发启动时还可能产生竞态。

建议：生产启动只执行 `alembic upgrade head`；迁移文件必须在开发阶段生成、审查、提交。

### 10. Refresh token 是纯无状态 JWT，无法撤销或检测重放

`create_refresh_token()` 只写入 `sub/exp/type`（`backend/app/core/security.py:20-22`），`AuthService.refresh_token()` 验签后直接签发新 token（`backend/app/services/auth_service.py:43-62`），没有 `jti`、会话表、轮换失效或登出撤销机制。

建议：引入 refresh token 会话表，存储哈希、`jti`、过期时间和撤销状态；刷新时轮换并使旧 token 失效。

## 中严重性（Medium）

### 11. 注册、登录、QA、分析请求缺少输入约束和限流

`UserRegister`/`UserLogin` 只声明裸字符串（`backend/app/schemas/auth.py:4-12`），QA 问题也没有长度限制（`backend/app/api/qa.py:19-20`）。配置中定义了 `MAX_VIDEO_DURATION_SECONDS` 和 `MAX_PARTS_PER_TASK`（`backend/app/core/config.py:28-31`），但 `AnalysisService.create_task()` 没有使用它们（`backend/app/services/analysis_service.py:25-40`）。

建议：用 Pydantic `Field(min_length/max_length)`、枚举和 URL 类型约束输入；对登录、注册、解析、创建任务、QA 调用增加用户/IP 级限流。

### 12. 重试任务实际会重跑所有子任务

`retry_task()` 只重置失败子任务（`backend/app/services/analysis_service.py:175-188`），但 worker 取出该任务下所有子任务并全部处理（`backend/app/workers/tasks/analyze_part.py:137-163`）。这会重新调用 ASR/LLM、浪费成本，并因全局删除逻辑覆盖已有成功结果。

建议：worker 只处理 `waiting`/失败后重置的子任务，跳过 `completed`。

### 13. ASR provider 选择逻辑与 LLM provider 不一致

LLM 工厂没有默认配置时会回退到用户第一条凭据（`backend/app/services/llm_factory.py:16-18`），但 ASR 只查询 `is_default=True` 的凭据（`backend/app/workers/tasks/analyze_part.py:317-336`）。用户已有凭据但未设默认时，总结可能可用，ASR 兜底却失败。

建议：复用同一个 provider 工厂逻辑，或在创建第一条凭据时由后端强制设为默认。

### 14. `get_part_analysis()` 对不存在的 part 返回 200

函数查询 `part = get_part_by_id()` 后没有判断（`backend/app/services/analysis_service.py:104`），即使 part 不存在也会返回 `status="unknown"` 的响应（`backend/app/services/analysis_service.py:152-163`）。

建议：part 不存在时返回 404。

### 15. Refresh token 的 `sub` 解析可能抛 500

`AuthService.refresh_token()` 在 `decode_token()` 后直接 `int(payload["sub"])`（`backend/app/services/auth_service.py:52`）。如果 token 缺少 `sub` 或格式不是整数，会产生 `KeyError`/`ValueError` 并冒泡为 500。

建议：复用 `get_current_user()` 中的防御式 claim 解析逻辑。

### 16. `Video.bvid` 只有索引没有唯一约束

模型声明 `bvid` 为普通索引（`backend/app/models/video.py:17`），仓储通过 `.first()` 读取（`backend/app/repositories/video_repository.py:6-7`）。并发解析同一视频可能插入重复记录，后续历史和 part 唯一约束都变得不可靠。

建议：给 `videos.bvid` 加唯一约束，并处理插入冲突。

### 17. OpenAI-compatible `response_format` 判断过宽

`OpenAICompatibleProvider` 对任何包含 `/v1` 的 base URL 都发送 `response_format={"type":"json_object"}`（`backend/app/integrations/llm/openai_compatible.py:42-44`）。DeepSeek、Ollama、LM Studio 等兼容接口未必支持该参数，可能直接 400。

建议：按 provider 能力配置是否启用 `response_format`，失败时降级为 prompt-only JSON。

### 18. 前端导出功能无法携带认证头，且组件未接入页面

`ExportMenu` 使用 `window.open(url, "_blank")`（`web/src/components/ExportMenu.tsx:7-17`），不会带上保存在 `localStorage` 中的 Bearer token；后端导出接口需要 `Authorization` header，因此会返回 401。当前代码中 `ExportMenu` 也没有被任何页面 import，导出入口不可见。

建议：用 `apiFetch` 拉取 blob 后创建下载链接，或改为短期签名下载 URL；把组件接入详情/分析页。

### 19. 前端 QA 发送后只追加助手消息，不显示用户刚发的问题

后端 `ask()` 会保存用户消息和助手消息（`backend/app/services/qa_service.py:139-155`），但接口只返回助手消息。前端 `handleSend()` 只把返回的助手消息 append 到列表（`web/src/pages/QAPage.tsx:47-55`），当前问题不会出现在聊天窗口，直到重新拉取历史。

建议：发送前乐观追加用户消息，或后端返回本轮 user + assistant 两条消息。

### 20. QA 检索对中文效果较弱且性能不可控

`_search_chunks()` 对问题做 `query.split()`，然后把每个 part 的所有 chunk 全量加载到内存逐个匹配（`backend/app/services/qa_service.py:32-45`）。中文问题通常没有空格，召回率会很低；长视频或大量 part 会导致查询变慢。

建议：先用数据库全文索引/向量检索，至少加入 chunk 数量上限和中文分词策略。

### 21. 前端 token 存储与设计文档不一致

前端把 access token 和 refresh token 都写入 `localStorage`（`web/src/api/client.ts:10-19`）。这与设计文档中 refresh token 使用 HttpOnly Cookie 的方向不一致，一旦出现 XSS，长期 refresh token 会被读取。

建议：refresh token 改用 HttpOnly、Secure、SameSite Cookie；access token 尽量只保存在内存。

## 低严重性与优化建议（Low）

### 22. `force_reanalyze` 字段没有实际控制缓存策略

任务创建保存了 `force_reanalyze`（`backend/app/services/analysis_service.py:41-47`），worker 处理时没有读取该字段，总是重新保存/删除结果。建议明确缓存策略：非强制时复用已有成功结果，强制时创建新版本。

### 23. 仓储函数内部频繁 commit，事务边界分散

`video_repository.create_video()`、`update_video()`、`create_video_part()` 等函数内部直接 `commit()`（`backend/app/repositories/video_repository.py:14-43`）。`VideoService.parse()` 过程中如果后续 part 同步失败，前面的视频记录已提交，容易留下部分数据。

建议：仓储只负责增删改查和 flush，事务由 service 层统一 commit/rollback。

### 24. ASR 长音频切片错误被静默忽略

OpenAI ASR 和 faster-whisper 对单片识别异常直接 `pass`（`backend/app/integrations/asr/openai_asr.py:38-43`、`backend/app/integrations/asr/faster_whisper_asr.py:60-66`），最后可能返回不完整甚至空结果，缺少可诊断错误。

建议：记录每个失败切片，超过失败比例时中止任务并暴露明确错误。

### 25. Python 依赖未锁版本

`backend/requirements.txt` 和 `pyproject.toml` 全部使用 `>=`（`backend/requirements.txt:1-13`、`backend/pyproject.toml:6-20`）。生产构建可能在不同时间解析出不同依赖版本。

建议：生成锁文件或使用精确版本范围，至少对 FastAPI/Pydantic/SQLAlchemy/Celery 做兼容性锁定。

### 26. Docker/配置文件存在重复和漂移

仓库同时存在 `web/docker/default.conf`、`docker/nginx/default.conf`、`docker/web-nginx.conf`。实际 `web/Dockerfile:9-11` 使用的是 `web/docker/default.conf`，其余配置容易过期；`docker/nginx/default.conf:28-34` 还包含嵌套 `location`，应验证 Nginx 是否接受。

建议：保留一个权威 Nginx 配置，删除或标记未使用文件。

### 27. 前端错误处理不一致

`QAPage` 加载会话失败时直接吞掉错误（`web/src/pages/QAPage.tsx:16-21`），`SettingsPage` 创建凭据失败时没有解析后端错误详情（`web/src/pages/SettingsPage.tsx:32-57`），删除凭据也没有 catch（`web/src/pages/SettingsPage.tsx:59-63`）。

建议：统一 API error helper，所有页面显示后端 `detail` 和网络错误状态。

## 建议修复顺序

1. 先修复会导致服务不可用的问题：QA `NameError`、worker 启动命令、`yt-dlp` 依赖和音频异常处理、`published_at` 类型。
2. 再补权限边界：视频详情/总结/导出/QA/分析结果的用户归属，明确全局缓存和用户私有数据的边界。
3. 调整 Docker 启动迁移策略，移除启动时 autogenerate。
4. 加输入校验、限流、refresh token 会话化和自定义 Base URL 防护。
5. 最后补测试：认证、权限隔离、QA 列表、导出、ASR fallback、任务重试、视频解析入库。
