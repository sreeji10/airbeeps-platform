## Airbeeps API (Supabase Integrated)

FastAPI backend with:
- Supabase Postgres (async SQLAlchemy + asyncpg)
- Supabase Auth JWT verification
- Supabase Storage dataset uploads
- chat sessions, message history, plan/run tracking
- LiteLLM-based response generation with streaming
- configurable agents + prompt templates
- background job queue + worker
- workspace/project scoped semantic memory
- evaluation datasets/runs/results
- usage tracking + workspace rate limits
- Alembic migrations

## 1) Configure environment

Create `apps/api/.env` from `apps/api/.env.example` and fill:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_SECRET_KEY`
- `LLM_MODEL`
- `LLM_PROVIDER` (e.g. `groq` for Groq OpenAI-compatible base URL)
- `LLM_API_KEY`

Notes:
- `SUPABASE_SECRET_KEY` is required by backend storage uploads.
- Do not expose `SUPABASE_SECRET_KEY` to frontend clients.

## 2) Install dependencies

From repo root:

```bash
uv sync --project apps/api --all-groups
```

## 3) Run database migrations

From `apps/api`:

```bash
uv run alembic -c alembic.ini upgrade head
```

From repo root (equivalent):

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
```

## 4) Run API

From repo root:

```bash
uv run --project apps/api uvicorn main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8000
```

## 4.1) Run background worker

From repo root:

```bash
uv run --project apps/api python -m airbeeps_api.worker
```

## 5) Authenticated API usage

Pass Supabase access token as Bearer token:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

Example endpoint:
- `GET /v1/auth/me` -> verifies JWT and returns current user + workspace memberships.

## 6) Chat workflow endpoints

- `POST /v1/chat/sessions` -> create a chat session
- `GET /v1/chat/sessions/{chat_id}/messages?workspace_id=...` -> fetch history
- `POST /v1/chat/sessions/{chat_id}/messages?workspace_id=...` -> run one chat turn
- `POST /v1/chat/sessions/{chat_id}/messages/stream?workspace_id=...` -> stream SSE tokens

Each chat turn creates:
- a `plan` row (placeholder execution plan)
- a `run` row with lifecycle `created -> running -> completed|failed`

Chat requests can include `agent_id` to run through a specific agent configuration.
When omitted, default runtime settings are used.

## 7) Storage upload endpoint

Use multipart upload:

- `POST /v1/datasets/upload`
- form fields:
  - `workspace_id`
  - `project_id`
  - `dataset_name`
  - `file` (binary)

On success:
- file stored in Supabase Storage bucket (`SUPABASE_STORAGE_BUCKET`)
- dataset + dataset_file metadata persisted in Postgres

## 8) Dev checks

From repo root:

```bash
uv run --project apps/api ruff check apps/api/src services libs tests
uv run --project apps/api mypy apps/api/src services libs tests
uv run --project apps/api pytest
```
