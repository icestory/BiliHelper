# BiliHelper 第二轮代码审查报告

审查日期：2026-04-30  
审查范围：M0-M5 全部代码（含 M5 新增：问答、导出、Chunk 聚合）  
审查方式：4 个 Agent 并行审查（backend core + services/API + integrations/workers + frontend/deploy）

---

## 严重问题 (CRITICAL) — 运行时一定崩溃

### 1. ASR 大文件处理：`output_dir` 未定义 → NameError

**文件：** `backend/app/integrations/asr/openai_asr.py:54` + `backend/app/integrations/asr/faster_whisper_asr.py:74`

两个 ASR provider 的 `transcribe()` 方法中，`_split_audio()` 在函数内部创建了 `output_dir` 局部变量但从未返回。外层直接使用 `os.rmdir(output_dir)` 导致 `NameError`。**任何超过 25MB（OpenAI）或 5 分钟（faster-whisper）的音频文件都会在 ASR 阶段崩溃。**

修复：`_split_audio` 返回 `(slices, output_dir)` 元组。

### 2. 导出端点完全无认证 — 任意用户可下载所有数据

**文件：** `backend/app/api/exports.py:12,29`

`download_video_md` 和 `download_part_md` 均无 `get_current_user` 依赖。任何人知晓 video_id/part_id 即可下载完整文案、总结、章节和问答记录。

修复：添加 `Depends(get_current_user)` + 服务层所有权校验。

### 3. QA 引用查询使用了错误的数据库列

**文件：** `backend/app/services/qa_service.py:195`

```python
.filter(VideoPart.video_id.in_([p for p in part_ids]), ...)
```

`part_ids` 是 `VideoPart.id` 列表（主键），但查询却比较了 `VideoPart.video_id`（外键），导致引用永远找不到正确的 part。所有问答引用中的 `part_id` 都会是 `None`。

修复：改为 `VideoPart.id.in_(part_ids)`。

### 4. yt-dlp 进程在 FFmpeg 失败时泄漏

**文件：** `backend/app/integrations/bilibili/audio.py:62-73`

`subprocess.run(ffmpeg_cmd)` 非超时异常（如 `CalledProcessError`）被通用 `except Exception` 捕获，但 `ytdlp_proc` 进程从未被杀死或回收。yt-dlp 子进程变为孤儿持续运行。

修复：异常处理块中增加 `ytdlp_proc.kill()`。

---

## 高严重性 (HIGH) — 影响功能正确性或数据完整性

### 5. 重试/reanalyze 导致重复数据

**文件：** `backend/app/workers/tasks/analyze_part.py:87,102,117`

`_save_transcript`、`_save_summary`、`_save_chapters` 均追加新记录而不删除旧记录。retry 时已完成的子任务被重新处理，创建重复的 transcript segment、part summary 和 chapter 记录。（`build_chunks` 正确先删后建，但 save 系列函数没有。）

修复：保存前先删除该 part_id 的旧记录。

### 6. `already_analyzed` 忽略当前用户

**文件：** `backend/app/services/video_service.py:49`

```python
self.db.query(AnalysisTask).filter(AnalysisTask.video_id == video.id).count() > 0
```

查询了所有用户的 AnalysisTask。用户 A 从未分析过的视频会因为用户 B 分析过而显示 `already_analyzed=True`。

修复：增加 `.filter(AnalysisTask.user_id == ...)` 条件。

### 7. Celery dispatch 前已提交数据库 — 任务可能永远卡在 waiting

**文件：** `backend/app/services/analysis_service.py:63+68, 186+189, 224+227`

`db.commit()` 在 `start_analysis.delay(task.id)` 之前执行。如果 Redis/Celery broker 不可达，`delay()` 抛出异常，但数据库已提交，task 记录 `status="waiting"` 却被永远不被处理。

修复：将 `commit` 移至 `delay` 之后，或增加 try/rollback。

### 8. QA Prompt 缺少 JSON 结构指令

**文件：** `backend/app/services/qa_service.py:17-26`

QA_PROMPT 未指定输出 JSON 格式，但代码调用了 `provider.chat_json()`（强制 `response_format: json_object`）。LLM 可能输出 `{"response": "..."}` 而非 `{"answer": "..."}`，导致用户收到空回复。

修复：Prompt 中明确要求 `{"answer": "..."}` 格式。

### 9. 视频总结生成失败被完全静默吞掉

**文件：** `backend/app/workers/tasks/analyze_part.py:296`

```python
except Exception:
    pass  # 视频总结失败不影响任务整体状态
```

无任何日志记录。生产环境排查全视频总结缺失问题时无法定位根因。

修复：至少添加 `logger.exception("视频总结生成失败")`。

### 10. 前端多处 Effect 缺少清理 — 陈旧响应覆盖新数据

**文件：**
- `web/src/pages/VideoDetailPage.tsx:12-28`
- `web/src/pages/TaskProgressPage.tsx:48-54`
- `web/src/pages/PartAnalysisPage.tsx:15-29`
- `web/src/pages/QAPage.tsx:15-33`

所有异步 fetch 的 useEffect 都没有 abort controller 或 cleanup flag。快速切换页面/routes 时，先发出的请求可能后返回，用陈旧数据覆盖正确的新数据。

修复：使用 `AbortController` 或 `let cancelled = false` cleanup 模式。

### 11. Token 失效后前端不重定向登录

**文件：** `web/src/api/client.ts:72-83`

当 refresh token 也失效（`refreshAccessToken()` 返回 false）时，API 返回 401，但 `clearTokens()` 未被调用，`AuthGuard` 仍允许通过。用户看到"加载失败"但无合法 token，无法恢复，直到手动刷新页面（M0 修复的 `loadTokens` 会清除问题）。

修复：refresh 失败后调用 `clearTokens()` 并导航到 `/login`。

### 12. QA 消息在错误时被静默清除

**文件：** `web/src/pages/QAPage.tsx:24-28`

```typescript
.then(r => r.ok ? r.json() : [])
.then(setMessages)
```

当 `getQAMessages` 返回非 2xx 时，`[]` 传给 `setMessages`，**清空**当前聊天窗口中的消息。切换会话时如果网络出现瞬时故障，已有消息会消失。

修复：非 OK 时保留当前消息或显示错误。

---

## 中严重性 (MEDIUM) — 可能引起异常行为

### 13. LLM `response_format: json_object` 与部分 provider 不兼容

**文件：** `backend/app/integrations/llm/openai_compatible.py:41`

非 OpenAI 的兼容 provider（Ollama、LM Studio 等）不支持 `response_format` 参数，可能返回 400 或静默降级为非 JSON 输出。

修复：可配置是否启用 `response_format`，或做 provider 特性检测。

### 14. `_validate_result` 章节时间比较可能 TypeError

**文件：** `backend/app/workers/tasks/analyze_part.py:417`

如果 LLM 返回字符串时间戳（如 `"start_time": "120"`），`st < prev_end` 比较 `str < int` 在 Python 3 引发 `TypeError`。虽被外层 catch 捕获标记为失败，但数据库中存储的是原始 TypeError 信息不友好。

### 15. `get_part_analysis` 权限检查只对最新子任务

**文件：** `backend/app/services/analysis_service.py:85-96`

子任务查询无条件取最新一条（不按用户过滤）。如果用户 B 在用户 A 之后分析了同一分 P，用户 A 再请求时看到的是用户 B 的子任务，被 403 拒绝 —— 尽管用户 A 自己也分析过。

修复：按当前用户的任务过滤子任务，或允许用户访问自己拥有的任意子任务。

### 16. `update_*` 函数跳过 None 值 — 无法清空字段

**文件：** `backend/app/repositories/credential_repository.py:49-50` + `video_repository.py:24-25`

`if value is not None: setattr(...)` 模式使得 API 调用者发送 `null` 意图清空某个字段时被默默忽略。

### 17. `update_video` 不刷新已有分 P 元数据

**文件：** `backend/app/services/video_service.py:82-83`

视频重新解析时，已有的分 P（cid 已存在）的 `title`、`duration`、`source_url` 不会被更新。如果 UP 主修改了分 P 标题或时长，数据库保留过时信息。

### 18. `_get_qa_provider` 从 Celery worker 导入私有函数

**文件：** `backend/app/services/qa_service.py:89`

```python
from app.workers.tasks.analyze_part import _get_llm_provider
```

Service 层导入 Worker 层的私有函数，架构边界被打破。重构 Worker 模块可能无声地破坏 QA 服务。

### 19. 多处缺少加载/错误反馈

**文件：**
- `QAPage.tsx:35-42` — 创建会话无 loading 状态，可重复点击
- `QAPage.tsx:54-56` — 提问失败静默忽略
- `ExportMenu.tsx:17` — 下载错误无用户反馈
- `HistoryPage.tsx:45-47` — 删除失败无反馈

### 20. `SubtitleSegment` 在循环内导入

**文件：** `backend/app/workers/tasks/analyze_part.py:211`

每次循环迭代重新执行 import 语句（虽然 Python 有缓存但仍有开销）。应移至文件顶部。

### 21. Docker Compose Web 构建流程不完整

**文件：** `docker-compose.yml:8` + `web/Dockerfile`

docker-compose 直接将 `./web/dist` 挂载到 nginx，但未定义 web 构建服务。`web/Dockerfile` 独立存在但不被 compose 引用。`docker compose up` 前必须手动 `cd web && npm run build`。

### 22. `prompt/summary_chapters_v1.txt` 缺少时间戳类型约束

Prompt 未明确要求 `start_time` 和 `end_time` 必须是数字而非字符串。部分 LLM 会输出字符串时间戳，导致校验失败。

---

## 低严重性 (LOW) — 代码质量问题

### 23. `Video.bvid` 有 index 但无 unique 约束

**文件：** `backend/app/models/video.py:17`

同一 BVID 可能被重复插入。`get_video_by_bvid` 用 `.first()` 返回任意一条。

### 24. `get_db` 缺少 `db.rollback()`

**文件：** `backend/app/core/database.py:11-17`

路由抛出异常时 session 直接 close 无 rollback。psycopg2 的失败事务可能污染连接池。

### 25. ASR Provider 两个实现中 `_split_audio` 和 `_get_audio_duration` 完全重复

**文件：** `openai_asr.py` vs `faster_whisper_asr.py`

相同逻辑在两处维护，修改一处需同步另一处。建议提取到 base 或公共工具模块。

### 26. `metadata.py` 中 `pubdate` 若为字符串 → TypeError

**文件：** `backend/app/integrations/bilibili/metadata.py:74`

`datetime.fromtimestamp(pubdate)` 不接收字符串。应增加 `isinstance(pubdate, (int, float))` 校验。

### 27. `resolver.py` 短链展开失败无日志

**文件：** `backend/app/integrations/bilibili/resolver.py:43-53`

`_expand_short_link` 捕获所有异常返回 None，不记录原因。b23.tv 链接变化时难以排查。

### 28. 前端 HistoryPage 分页无上限

**文件：** `web/src/pages/HistoryPage.tsx:88-91`

`total` 和 `page_size` 被 API 返回但未使用。"下一页"按钮永远可点击（即使已在最后一页）。

### 29. Nginx 缺少 gzip 压缩和 API 健康检查

**文件：** `docker/nginx/default.conf` + `docker-compose.yml:13`

静态资源无 gzip（JS bundle ~200KB 未压缩传输）；API 无 healthcheck（nginx 依赖只检查启动不检查健康）。

### 30. 硬编码默认 SECRET_KEY

**文件：** `backend/app/core/config.py:10`

`APP_SECRET_KEY: str = "change-me-in-production"` — 不覆盖环境变量可直接伪造 JWT token。

---

## 问题统计

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 4 |
| HIGH | 8 |
| MEDIUM | 10 |
| LOW | 8 |
| **总计** | **30** |

---

## 优先修复顺序

1. **ASR `output_dir` NameError** (#1) — 大音频文件 ASR 直接崩溃
2. **导出端点无认证** (#2) — 全量数据暴露
3. **QA 引用查询列错误** (#3) — 引用功能完全不工作
4. **yt-dlp 进程泄漏** (#4) — 长时间运行导致资源耗尽
5. **重复数据** (#5) — 重试造成数据库膨胀
6. **`already_analyzed` 跨用户** (#6) — 用户界面信息误导
7. **Celery dispatch 时序** (#7) — 任务卡在 waiting 状态
8. **前端陈旧响应竞争** (#10) — 快速操作显示错误数据
