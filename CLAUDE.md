# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

BiliHelper is a personal-use Bilibili (B站) video content parser, summarizer, and Q&A tool. Users submit Bilibili video links via Web or Android, and the system extracts transcripts (subtitles or ASR fallback), generates summaries and chapter divisions, supports Q&A against video content, and exports Markdown.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12+ / FastAPI |
| Data validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Database | PostgreSQL (SQLite for local dev only) |
| Task queue | Celery + Redis |
| Web frontend | React + TypeScript + Vite |
| Web data fetching | TanStack Query |
| Web routing | React Router |
| Android | Kotlin + Jetpack Compose |
| Android networking | Retrofit + OkHttp |
| Deployment | Docker Compose |

## Repo structure (planned)

```
BiliHelper/
  docs/                     # Product and technical design docs (already exist)
  backend/
    app/
      main.py               # FastAPI app entry point
      api/                   # Route handlers (auth, videos, tasks, qa, exports)
      core/                  # Config, security, dependencies
      models/                # SQLAlchemy ORM models
      schemas/               # Pydantic request/response schemas
      services/              # Business logic orchestration
      integrations/          # External adapters (bilibili, asr, llm, embedding)
      workers/               # Celery task definitions
      prompts/               # Versioned LLM prompt templates
      exporters/             # Markdown generation
      repositories/          # Data access layer
    migrations/              # Alembic migrations
    tests/
    pyproject.toml
  web/
    src/
      api/                   # API client layer
      components/            # Reusable UI components
      pages/                 # Route-level page components
      routes/                # React Router config
      stores/                # Global state (if needed)
      types/                 # TypeScript type definitions
    package.json
    vite.config.ts
  android/
    app/
    build.gradle.kts
  docker/
    nginx/
  docker-compose.yml
  .env.example
```

## Architecture principles

- **Thin clients, fat backend**: Web and Android only handle UI, auth, and task polling. All heavy work (Bilibili parsing, subtitle fetching, ASR, LLM calls, Markdown export) runs on the backend.
- **Bilibili adapter isolation**: All Bilibili-specific logic lives in `integrations/bilibili/` (resolver, metadata, subtitles, audio extraction). Business code never calls Bilibili APIs directly.
- **Provider abstraction for LLM/ASR**: LLM and ASR are behind provider interfaces (`integrations/llm/`, `integrations/asr/`). First version supports OpenAI-compatible APIs, but the interface must not bind to a single vendor.
- **No video files stored**: Temporary audio files for ASR are cleaned up after the task completes or fails. Only text/structured results are persisted.
- **API keys encrypted at rest**: User LLM API keys and Bilibili cookies are AES-GCM encrypted with a server-side master key, never returned to clients.
- **Prompt versioning**: All LLM prompts carry a `prompt_version` field stored alongside results for traceability.

## Code style

在必要的地方编写中文注释，提高项目代码可读性。关键逻辑、业务规则、非显而易见的处理流程都应使用中文注释说明。

## Key data model tables

- `users`, `api_credentials` — auth and user-managed LLM configs
- `videos`, `video_parts` — Bilibili video metadata and multi-part episodes
- `analysis_tasks`, `part_analysis_tasks` — async task tracking with status state machines
- `transcript_segments`, `transcript_chunks` — subtitle/ASR text (fine-grained segments + aggregated chunks for Q&A retrieval)
- `part_summaries`, `chapters`, `video_summaries` — LLM-generated structured results
- `qa_sessions`, `qa_messages` — Q&A history with citations

## Core processing flow

1. User submits Bilibili URL → `POST /videos/parse` resolves metadata and part list
2. User selects analysis scope → `POST /analysis-tasks` creates tasks and enqueues Celery job
3. Worker fetches subtitles (or extracts temp audio → ASR fallback), then calls LLM for summary + chapters
4. Frontend polls `GET /analysis-tasks/{id}` for status; completed results include transcript, summary, chapters
5. Q&A: `POST /qa-sessions/{id}/messages` retrieves relevant transcript chunks and calls LLM with citations

Detailed docs: `doc/BiliHelper_Product.md` (features, scope), `doc/BiliHelper_Technical_Design.md` (architecture, data model, API design, security).

## Common commands (once code is initialized)

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
alembic upgrade head
pytest
pytest -k "test_name"                          # single test
celery -A app.workers.celery_app worker --loglevel=info

# Web
cd web
npm install
npm run dev
npm run build
npm test

# Docker (full stack)
docker compose up -d
docker compose logs -f worker
```
