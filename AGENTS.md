# Repository Guidelines

## Project Structure & Module Organization
Airbeeps is a modular monorepo.

- `apps/api/`: FastAPI backend entrypoint, API routes, config, DB session, migrations.
- `apps/web/`: frontend app (kept separate from backend changes).
- `services/`: business logic by domain (`runtime`, `rag`, `ingestion`, `jobs`, `memory`, `evaluation`, etc.).
- `libs/`: shared contracts and primitives (`db` models, `schemas`, `llm`, `tools`, embeddings).
- `tests/`: backend unit/integration tests.
- `docs/`: architecture and design docs.

Keep business logic out of route handlers; routes should orchestrate services only.

## Build, Test, and Development Commands
Use `uv` for all Python workflows.

- Install/sync deps: `uv sync --project apps/api --all-groups`
- Apply migrations: `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
- Run API locally: `uv run --project apps/api uvicorn main:app --app-dir apps/api --reload --host 0.0.0.0 --port 8000`
- Run worker loop: `uv run --project apps/api python -m airbeeps_api.worker`
- Lint: `uv run --project apps/api ruff check apps/api/src services libs tests`
- Type check: `uv run --project apps/api mypy apps/api/src services libs tests`
- Tests: `uv run --project apps/api pytest`

Frontend workflows (Bun + Next.js):

- Install deps: `bun install` (run in `apps/web`)
- Build: `bun run build` (run in `apps/web`)
- Dev server: `bun run dev -- --port 3015` (run in `apps/web`)
- Prod server: `bun run start -- --port 3015` (run in `apps/web`)

## Coding Style & Naming Conventions
- Python 3.13, 4-space indentation, explicit typing preferred.
- Follow `ruff` + `mypy` strict settings in `apps/api/pyproject.toml`.
- Files/modules: `snake_case`; classes: `PascalCase`; functions/variables: `snake_case`.
- Pydantic schemas live in `libs/schemas`; service classes in `services/<domain>/service.py`.
- Keep changes ASCII unless file already uses Unicode.

## Testing Guidelines
- Framework: `pytest` (+ `pytest-cov` configured in project).
- Test files: `tests/test_*.py`; test names: `test_<behavior>()`.
- Add/update tests for service and API changes, especially runtime state, auth checks, and migrations.

## Commit & Pull Request Guidelines
- Commit style follows Conventional Commits seen in history, e.g.:
  - `feat(runtime): add planner fallback`
  - `fix(auth): handle ES256 Supabase JWT`
- PRs should include:
  - clear summary and scope
  - migration notes (if schema changed)
  - commands run (`ruff`, `mypy`, `pytest`)
  - API contract changes (request/response examples)

## Security & Configuration Tips
- Never hardcode credentials; use env vars (`DATABASE_URL`, `SUPABASE_URL`, keys, LLM settings).
- Prefer least-privilege keys; keep service-role keys server-side only.

## Current Integration Notes (March 2026)
- Auth supports email/password login via backend endpoint `POST /v1/auth/login`.
- Frontend login flow is email/password first, with token login kept as advanced fallback.
- Next.js backend proxy endpoint is `apps/web/app/api/backend/[...path]/route.ts`.
- Chat streaming remains SSE-based via backend stream endpoints (frontend has no LLM logic).
- Dashboard metrics are backend-driven (agents, chat sessions, datasets, jobs/usage).
- Runs and Knowledge pages use server-filtered/paginated table workflows.

## Migration and Troubleshooting Notes
- If `GET /v1/agents` or `GET /v1/jobs` returns `500`, first run:
  - `uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head`
- A recent failure mode was missing tables from unapplied migrations (for agent platform modules).
- Quick health checks:
  - API: `curl http://127.0.0.1:8000/health`
  - Web: `curl http://127.0.0.1:3015/login`
