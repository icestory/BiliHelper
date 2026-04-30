# BiliHelper 代码审查报告

审查日期：2026-04-29  
审查范围：M0-M4 全部代码（后端 + 前端 + 部署配置）

---

## 严重问题 (CRITICAL) — 必须修复才能运行

### 1. Worker 中未定义变量 `total` → NameError

**文件：** `backend/app/workers/tasks/analyze_part.py`  
**行号：** 284, 291, 293, 296

变量 `total` 使用了四次但从未赋值。缺少 `total = len(subs)`。任何 completed/partial_failed 的分析任务都会触发 `NameError`，导致整个分析管道不可用。

```python
# 缺少：total = len(subs)
if completed > 0 and total > 0:   # NameError
    ...
if completed == total:             # NameError
```

### 2. `loadTokens()` 从未调用 — 页面刷新后认证丢失

**文件：** `web/src/api/client.ts` + `web/src/main.tsx`  
**行号：** client.ts:16-19

`loadTokens()` 已导出但从未被导入或调用。页面刷新后，内存中的 `accessToken` 和 `refreshToken` 保持为 `null`（虽然 localStorage 中有 token）。所有 API 调用因为缺少 Authorization header 而返回 401，用户被迫每次刷新后重新登录。

修复：在 `main.tsx` 中应用渲染前调用 `loadTokens()`。

### 3. Encryption key 无效 — 任何加密操作都会 crash

**文件：** `.env.example` + `backend/app/core/security.py`  
**行号：** .env.example:7, security.py:45

`.env.example` 中的 `CREDENTIAL_ENCRYPTION_KEY=generate-with-fernet-generate-key` 不是有效的 base64 32 字节 Fernet key。`Fernet(key)` 将抛出 `ValueError`。API Key 的加解密全部不可用。

### 4. Docker Compose 缺少 `.env` 文件 — 无法启动

**文件：** `docker-compose.yml`  
**行号：** 18, 33

`docker-compose.yml` 引用 `env_file: .env`，但该文件不存在（仅有 `.env.example`）。`docker compose up` 会直接失败。

---

## 高严重性 (HIGH) — 影响功能正确性

### 5. JWT `sub` 缺失/非数字 → 500 错误

**文件：** `backend/app/core/dependencies.py`  
**行号：** 26

`payload["sub"]` 直接访问字典键。如果 token 解码成功但缺少 `"sub"`（KeyError），或 `"sub"` 为非数字字符串（ValueError），会返回 500 而非 401。应使用 `payload.get("sub")` 并捕获类型转换异常。

### 6. Refresh token 可作为 Access token 使用

**文件：** `backend/app/core/security.py` + `dependencies.py`  
**行号：** security.py:26, dependencies.py:19-26

`decode_token` 不验证 `type` claim。refresh token （`"type": "refresh"`，有效期 30 天）可被当作 access token 使用，绕过短期过期策略。

### 7. `get_part_analysis` 无权限检查 — 任意用户可读取任意分 P 数据

**文件：** `backend/app/services/analysis_service.py`  
**行号：** 80

`get_part_analysis(part_id)` 不接受 `user_id` 参数，不检查所有权。API 路由获取了 `current_user` 但未传递给 service。任何认证用户可查看任意视频的文案、总结和章节。

### 8. `get_video_summary` 无认证依赖 — 公开访问

**文件：** `backend/app/api/videos.py`  
**行号：** 49-50

`GET /api/videos/{video_id}/summary` 没有 `get_current_user` 依赖，是该文件唯一不需要认证的端点，任何人都可访问。

### 9. B站 API 返回 `"owner": null` 时 metadata 解析崩溃（AttributeError）

**文件：** `backend/app/integrations/bilibili/metadata.py`  
**行号：** 62-63

```python
owner_name=data.get("owner", {}).get("name", ""),
```

`data.get("owner", {})` 仅在键缺失时返回 `{}`。如果 API 返回 `"owner": null`，则返回 `None`，`.get("name")` → `AttributeError`。已删除/受限视频会触发此 bug。

### 10. ASR 音频 yt-dlp 假阳性超时

**文件：** `backend/app/integrations/bilibili/audio.py`  
**行号：** 66

```python
ytdlp_proc.wait(timeout=5)
```

ffmpeg 成功完成后给 yt-dlp 进程仅 5 秒退出时间。yt-dlp 清理网络连接可能需要更久。实际超时只有 5 秒（不是错误消息中说的"15 分钟"），合法的音频提取被误判为失败。

### 11. `VideoPreview.tsx` 中 `video.id!` 强制解包可能传 null

**文件：** `web/src/components/VideoPreview.tsx`  
**行号：** 41

`video.id!` 使用 TypeScript 非空断言，但运行时 `video.id` 可能是 `null`。这会发送 `"video_id": null` 给后端 API。

### 12. `TaskProgressPage.tsx` setInterval 泄漏

**文件：** `web/src/pages/TaskProgressPage.tsx`  
**行号：** 56-71

`handleRetry` 创建新 `setInterval` 前不清除旧 interval。每次重试增加一个轮询定时器。组件卸载时只清除最新的 interval，旧的持续运行导致多倍轮询。修复： `clearInterval(intervalRef.current)` 在 `setInterval` 之前。

### 13. `HistoryPage.tsx` 删除操作存在竞态条件

**文件：** `web/src/pages/HistoryPage.tsx`  
**行号：** 42

```typescript
setItems(items.filter((i) => i.id !== videoId));
```

使用闭包中的 `items` 而非函数式更新。快速连续删除两个条目时，第二个删除会覆盖第一个删除的效果，被删除的条目重新出现。

### 14. 多处页面错误状态在路由变化时残留

**文件：** `web/src/pages/VideoDetailPage.tsx` (行 12-27), `PartAnalysisPage.tsx` (行 15-28)

`videoId` 或 `partId` 变化时，`setLoading(true)` 被调用但 `setError("")` 没有被调用。前一次请求的错误信息残留显示，即使新请求成功。

---

## 中严重性 (MEDIUM) — 可能引起异常行为

### 15. `_validate_result` 中 `prev_end` 可能为 None → TypeError

**文件：** `backend/app/workers/tasks/analyze_part.py`  
**行号：** 399-406

LLM JSON 输出中若章节的 `end_time` 字段存在但值为 `null`，`ch.get("end_time", st)` 返回 `None`（因为键存在）。下一次迭代 `int < None` → `TypeError`。

### 16. `mask_api_key` 对短 key 暴露过多

**文件：** `backend/app/services/credential_service.py`  
**行号：** 10-14

8 位 key `"12345678"` → mask 后 `"123****5678"`（显示 7/8 = 87.5%）。8-11 位 key 的脱敏效果很差。

### 17. `openai_compatible.py` 对异常 API 响应结构缺少防御

**文件：** `backend/app/integrations/llm/openai_compatible.py`  
**行号：** 48

```python
content = data["choices"][0]["message"]["content"]
```

如果 API 返回 `{"choices": []}` 或 `{"choices": [{"message": null}]}`，直接 `KeyError`/`IndexError`。应在访问前检查结构完整性。

### 18. ASR 临时目录泄漏

**文件：** `backend/app/integrations/asr/openai_asr.py` (行 93), `faster_whisper_asr.py` (行 97)

`tempfile.mkdtemp()` 创建的目录在切片文件删除后从未被删除，每次大文件 ASR 请求泄漏一个空目录。

### 19. Video 和 Parts 创建非原子性

**文件：** `backend/app/services/video_service.py`  
**行号：** 53, 74

`create_video` 单独 commit，然后每个 `create_video_part` 独立 commit。部分 parts 创建失败时，video 记录和已创建的 parts 已持久化，数据库处于不一致状态。

### 20. Repository 层函数各自独立 commit

**文件：** 所有 `backend/app/repositories/*.py`

每个 `create_*`、`update_*`、`delete_*` 都自行 `db.commit()`。Service 层无法将多个操作纳入同一事务。标准模式是 commit 在 service 层完成。

### 21. `get_video_history` 中 `status` 参数死代码

**文件：** `backend/app/repositories/video_repository.py`  
**行号：** 47-72

函数签名接受 `status: str | None = None` 但从不在查询中应用。`count_video_history` 甚至不接受该参数。

### 22. `force_reanalyze` 保存但从未被检查

**文件：** `backend/app/services/analysis_service.py`  
**行号：** 42

标记被存储但创建新任务前不检查是否已有分析结果。即使 `force_reanalyze=False` 也能创建冗余任务。

### 23. LLM Provider 和 ASR Provider 的空 prompt 无声失败

**文件：** `backend/app/workers/tasks/analyze_part.py`  
**行号：** 167

如果 `prompts/summary_chapters_v1.txt` 缺失或为空，LLM 以 `system_prompt=""` 运行，输出不可预测，任务失败但错误消息不提及 prompt 丢失。

### 24. 保存摘要时 provider/model 元数据可能错误标记为 "unknown"

**文件：** `backend/app/workers/tasks/analyze_part.py`  
**行号：** 266-268

`_get_llm_provider` 可回退到非默认凭据，但 `_get_cred` 只找默认凭据。使用非默认凭据时，metadata 标记为 `provider="unknown"`。

### 25. 前端认证路由无守卫

**文件：** `web/src/routes/index.tsx`  
**行号：** 10-18

受保护页面（`/history`, `/videos/new`, `/tasks/:taskId` 等）不经认证直接可访问。如果 token 丢失（问题 2），用户看到错误而非被重定向到登录页。

### 26. `@tanstack/react-query` 未使用 — 死代码

**文件：** `web/src/main.tsx`  
**行号：** 4, 8, 12

`QueryClientProvider` 和 `QueryClient` 被导入初始化但整个项目没有使用 React Query hooks。增加了不必要的 bundle 体积。

### 27. API client 并发 401 刷新竞态条件

**文件：** `web/src/api/client.ts`  
**行号：** 65-71

两个请求同时得到 401 时，并发调用 `refreshAccessToken()`。第一个成功，第二个使用已被废止的旧 refresh token 导致失败。

### 28. 缺少 `.dockerignore` 文件

**文件：** `backend/` 和 `web/` 目录

`backend/Dockerfile` 的 `COPY . .` 会复制 `.venv/`（数百 MB）、`__pycache__/`、潜在的 `.env` 文件到镜像中。`web/Dockerfile` 类似问题复制 `node_modules/`。

### 29. Celery Worker 异常处理中二次数据库查询可能失败

**文件：** `backend/app/workers/tasks/analyze_part.py`  
**行号：** 304-312

外层异常处理在异常上下文中执行新的数据库查询更新 task 状态。如果数据库连接已断开，此查询同样失败，阻止 `self.retry()` 执行并吞掉原始错误。

### 30. `pyproject.toml` 与 `requirements.txt` 无同步机制

**文件：** `backend/pyproject.toml` + `backend/requirements.txt`

Dockerfile 使用 `requirements.txt`，但权威依赖列表在 `pyproject.toml`。两文件可能不同步，导致 Docker 镜像安装了过时/错误的依赖版本。

### 31. Redis 无 healthcheck

**文件：** `docker-compose.yml`  
**行号：** 58

`redis` 服务没有 healthcheck，`api` 和 `worker` 使用 `condition: service_started`。在冷启动竞态中，Celery broker 可能在 Redis 真正接受连接前尝试连接。

### 32. FTP 读取环境变量绕过 pydantic-settings

**文件：** `backend/app/integrations/bilibili/audio.py`  
**行号：** 93

`os.getenv("TEMP_FILE_TTL_HOURS", "24")` 直接读取 OS 环境变量，绕过了 `config.py` 的 `Settings` 对象。如果通过 `.env` 文件配置，两者可能不一致。

---

## 低严重性 (LOW) — 代码质量问题

### 33. 多个 ORM 模型缺少时间戳列

**文件：** `backend/app/models/task.py`, `transcript.py`, `summary.py`

- `PartAnalysisTask` 有 `started_at`/`finished_at` 但无 `updated_at`
- `TranscriptSegment`、`TranscriptChunk` 无任何时间戳
- `Chapter` 无时间戳

### 34. repository 的 `update_*` 函数跳过 None 值

**文件：** `backend/app/repositories/credential_repository.py` (行 50), `video_repository.py` (行 24)

`if value is not None: setattr(...)` → 调用者无法将字段设为 NULL。与 PATCH 语义冲突。

### 35. `unset_default_for_user` 竞态条件

**文件：** `backend/app/services/credential_service.py`  
**行号：** 41-56

两个并行请求可能同时将多个凭据设为默认。缺少 `(user_id, is_default)` 唯一约束或咨询锁。

### 36. `schemas/auth.py` 未使用的 `EmailStr` 导入

**文件：** `backend/app/schemas/auth.py`  
**行号：** 2

`EmailStr` 被导入但 `UserRegister.email` 类型为 `str | None`。

### 37. `api/auth.py` 中未使用的 `user` 变量

**文件：** `backend/app/api/auth.py`  
**行号：** 16, 23

`register` 和 `login` 返回 `(user, access, refresh)`，但 `user` 未被使用（Linter 警告）。

### 38. Pydantic v1 弃用的 `Config` 内部类

**文件：** `backend/app/core/config.py`  
**行号：** 37-38

应使用 Pydantic v2 的 `model_config = SettingsConfigDict(...)`。

### 39. `resolver.py` 短链展开异常静默吞咽

**文件：** `backend/app/integrations/bilibili/resolver.py`  
**行号：** 43-53

`_expand_short_link` 捕获所有异常返回 `None`，不记录日志。b23.tv 链接格式变化时难以排查。

### 40. `metadata.py` 中 `if pubdate:` 对 Unix timestamp 0 为假

**文件：** `backend/app/integrations/bilibili/metadata.py`  
**行号：** 72

`if pubdate:` 在时间戳为 0 (1970-01-01) 时为 False。应使用 `if pubdate is not None:`。

### 41. `faster_whisper_asr.py` 中 `confidence = avg_logprob` 语义不对

**文件：** `backend/app/integrations/asr/faster_whisper_asr.py`  
**行号：** 82

`avg_logprob` 为负数（如 -0.3），而 `TranscriptSegment.confidence` 字段预期 0-1 范围。

### 42. 前端 `formatTime` 不处理负数或 NaN

**文件：** `web/src/types/analysis.ts`  
**行号：** 55-59

输入负数返回 `"-1:XX"`，NaN 返回 `"NaN:NaN"`。缺少运行时校验。

### 43. `ChapterList.tsx` 和 `TranscriptView.tsx` 使用 index 作为 key

**文件：** `web/src/components/ChapterList.tsx` (行 17), `TranscriptView.tsx` (行 29)

动态列表不应使用数组 index 作为 React key。

### 44. `TranscriptView.tsx` 多个段落可能竞用同一 ref

**文件：** `web/src/components/TranscriptView.tsx`  
**行号：** 26-30

如果 `highlightTime` 同时落入多个重叠时间段，多个 `<div>` 竞争同一个 ref。React 只赋值给最后一个匹配元素。

### 45. Nginx 缺少安全响应头和缓存头

**文件：** `docker/nginx/default.conf`

- 无 `X-Content-Type-Options`、`X-Frame-Options`、`CSP`
- 静态资源无 `Cache-Control`（SPA index.html 应 `no-cache`，带 hash 的 JS/CSS 应长缓存）

### 46. web/Dockerfile 只有 build stage，无 runtime 镜像

**文件：** `web/Dockerfile`

Dockerfile 仅产出 `/app/dist`。Docker Compose 依赖主机上已存在 `web/dist/` 目录。没有自动化构建依赖。

### 47. docker-compose 中硬编码数据库密码

**文件：** `docker-compose.yml`  
**行号：** 48-50

`POSTGRES_PASSWORD: bilihelper` 硬编码而非引用环境变量。

---

## 问题统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 4 |
| HIGH | 10 |
| MEDIUM | 18 |
| LOW | 15 |
| **总计** | **47** |

---

## 严重问题优先修复顺序

1. **Worker `total` 未定义** (#1) — 分析管道完全不可用
2. **`loadTokens()` 未调用** (#2) — 前端每次刷新丢登录态
3. **Encryption key 无效** (#3) — API Key 加解密 crash
4. **Docker 缺少 `.env`** (#4) — 无法启动
5. **JWT 验证漏洞** (#5, #6) — 安全边界问题
6. **权限检查缺失** (#7, #8) — 数据越权访问
7. **B站 API 解析崩溃** (#9) — 特定视频完全无法处理
8. **前端 setInterval 泄漏** (#12) — 逐步耗尽资源
9. **前端非空断言** (#11) — 潜在运行时错误
