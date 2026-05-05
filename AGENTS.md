# Repository Guidelines

## Project Structure & Module Organization

BiliHelper is split into a FastAPI backend and a Vite/React frontend. Backend code lives in `backend/app/`: `api/` routes, `core/` config, `models/` ORM, `schemas/` Pydantic models, `services/` business logic, `repositories/` data access, `integrations/` Bilibili/LLM/ASR adapters, `workers/` Celery tasks, and `prompts/` versioned prompts. Alembic migrations are in `backend/migrations/`. Frontend code lives in `web/src/`: `api/`, `components/`, `pages/`, `routes/`, `types/`, and `assets/`. Deployment config is in `docker/` and `docker-compose.yml`; docs are in `doc/`.

## Build, Test, and Development Commands

- `docker compose up -d`: run web, API, worker, PostgreSQL, and Redis.
- `cd backend && pip install -e ".[dev]"`: install backend runtime and dev tools.
- `cd backend && alembic upgrade head`: apply database migrations.
- `cd backend && uvicorn app.main:app --reload`: run the API locally.
- `cd backend && celery -A app.workers.celery_app worker --loglevel=info`: run analysis jobs.
- `cd backend && pytest`: run backend tests.
- `cd backend && ruff check app`: lint backend Python.
- `cd web && npm install`: install frontend dependencies.
- `cd web && npm run dev`: start Vite.
- `cd web && npm run lint`: run ESLint.
- `cd web && npm run build`: type-check and build the frontend.

## Coding Style & Naming Conventions

Use Python 3.12+ with typed FastAPI/Pydantic/SQLAlchemy code. Keep orchestration in `services/`, persistence in `repositories/`, and provider details in `integrations/`. Use `snake_case` for Python files, functions, and variables; `PascalCase` for ORM/Pydantic classes. Frontend code uses TypeScript and React function components. Name components/pages with `PascalCase.tsx`; keep API modules domain-based, such as `videos.ts`. Add concise Chinese comments for unclear business rules.

## Testing Guidelines

Add backend tests under `backend/tests/` with `test_*.py` names and pytest-style test functions. Prioritize service and repository tests for task states, credentials, Bilibili parsing, transcripts, and exports. No frontend test runner is configured; for UI changes, run `npm run lint` and `npm run build`.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit prefixes, for example `feat:`, `fix:`, and `docs:`. Keep commits scoped; Chinese descriptions are acceptable when consistent with history. Pull requests should include a summary, linked issues when applicable, migration notes for schema changes, screenshots for UI changes, and verification commands.

## Security & Configuration Tips

Never commit real `.env` files, API keys, Bilibili cookies, or generated secrets. Use `.env.example` as the template. Preserve credential encryption and temporary media cleanup behavior.
