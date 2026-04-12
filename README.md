# LLM-powered Translation Agent

**Whole-book English → Chinese translation agent.** EPUB or PDF in, bilingual or Chinese-only HTML / Markdown / EPUB / PDF out — with packet-level retries, Kubernetes-style reconciliation, and a self-healing runtime.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![PostgreSQL 16](https://img.shields.io/badge/postgres-16-336791)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![React](https://img.shields.io/badge/frontend-React%20%2B%20TS-61DAFB)
![License](https://img.shields.io/badge/license-MIT-green)

## Quick Start

Only **one** variable is required: `OPENAI_API_KEY`.

### Docker (recommended)

```bash
git clone https://github.com/1055373165/DLERHY.git
cp .env.example .env   # set OPENAI_API_KEY=sk-...
docker compose up -d   # → http://localhost:58000
```

Docker Compose brings up PostgreSQL 16 and the app container. Uploads persist in `app_exports`; database in `postgres_data`.

### Local (macOS)

```bash
git clone https://github.com/1055373165/DLERHY.git
cp .env.example .env   # set OPENAI_API_KEY=sk-...
./dev.sh               # → http://localhost:4173
```

`dev.sh` installs Python deps (via `uv`), frontend `node_modules`, runs Alembic migrations, and boots backend + frontend.

> Upload `.epub` or `.pdf` in the **WORK** workspace → **Bootstrap** → **Translate**. Progress streams live.

---

## Why Book Agent

- **Packet-level atomicity** — the translation unit is 3–8 sentences, not a whole chapter. An HTTP 429 or malformed LLM response re-runs one packet; the other 99% stay untouched.
- **Kubernetes-style reconciliation** — stateless controllers watch PostgreSQL and push toward desired state. Kill any process at any time; the next reconcile tick reads the DB and resumes.
- **Self-healing runtime** — exceptions are classified into retry / pause / incident. Stalled leases are auto-reclaimed. Runtime anomalies generate `PatchProposal`s that can auto-apply within budget.
- **Deterministic fix routing** — review issues map to 12 predefined action types (`RERUN_PACKET`, `UPDATE_TERMBASE_THEN_RERUN_TARGETED`, `REPARSE_CHAPTER`, …) — no black-box "LLM fixes itself".
- **8-worker parallelism** — PostgreSQL provides concurrency safety; per-chapter lane isolation ensures context consistency. Adjustable per run via the budget field.
- **Any OpenAI-compatible backend** — DeepSeek, OpenAI, Moonshot, local vLLM — swap `OPENAI_BASE_URL` and `BOOK_AGENT_TRANSLATION_MODEL`.

---

## Architecture

![d2 (4)](https://github.com/user-attachments/assets/b2704e3f-8872-46e9-b12b-b64487af9a12)

**The key insight:** nothing in the data plane holds state. Kill any worker, any controller, any backend process — the next reconcile tick reads PostgreSQL, sees what's missing, and resumes. No orchestration bus, no task queue, no in-memory state to lose.

---

## Configuration

Only `OPENAI_API_KEY` is required. Copy `.env.example` for the full list.

| Variable | Default | Note |
|----------|---------|------|
| `OPENAI_API_KEY` | — | **Required.** Any OpenAI-compatible provider |
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | Change to swap providers |
| `BOOK_AGENT_TRANSLATION_MODEL` | `deepseek-chat` | Model identifier |
| `BOOK_AGENT_DATABASE_URL` | `postgresql+psycopg://…@localhost:55432/book_agent` | Docker and `dev.sh` both use port `55432` |
| `BOOK_AGENT_TRANSLATION_TIMEOUT_SECONDS` | `120` | Per-request LLM timeout |
| Per-run `max_parallel_workers` | `8` | Set via the run budget field in UI or API |

---

## Run Control API

The full translation lifecycle is REST-addressable:

```
GET  /v1/runs/{id}              # status, budget, stage progress
GET  /v1/runs/{id}/events       # paginated audit event stream
POST /v1/runs/{id}/pause        # graceful pause at next safe point
POST /v1/runs/{id}/resume       # resume from checkpoint
POST /v1/runs/{id}/retry        # reset retryable_failed items
POST /v1/runs/{id}/cancel       # hard stop
```

The frontend polls every 2.5s when a run is active — the UI is a live view of PostgreSQL, not a cached snapshot.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic 2 · Alembic |
| Frontend | React 18 · TypeScript · Vite · React Query |
| Database | PostgreSQL 16 (sole storage — no Redis, no MQ) |
| PDF | PyMuPDF |
| LLM | httpx → any OpenAI-compatible endpoint, structured output |
| Deploy | Docker Compose · uvicorn · uv |

---

## License

MIT
