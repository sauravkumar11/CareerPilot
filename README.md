# CareerPilot AI

An AI copilot for the software engineering job search: discovers jobs from public ATS
APIs, scores fit against your resume with Google Gemini, and tracks your pipeline.

This is a **working vertical slice**, not the entire spec from the original brief.
See "What's built" vs. "What's not built yet" below before treating this as a finished
product.

## Architecture

```
careerpilot-ai/
  backend/    FastAPI + PostgreSQL + Redis/Celery, clean architecture
    app/
      core/          config, security (JWT/bcrypt), celery app
      db/            async SQLAlchemy engine/session, portable UUID type
      domain/
        models/      SQLAlchemy ORM models
        schemas/      Pydantic request/response schemas
      repositories/   repository pattern, one per aggregate
      services/       business logic (auth, job discovery, AI matching)
        ats_adapters/ Greenhouse / Lever / Ashby / SmartRecruiters clients
      api/v1/         FastAPI routers
      tasks/          Celery tasks (scheduled job sync)
    alembic/          DB migrations
    scripts/          init_db.py, seed_companies.py
    tests/            pytest + httpx mock transport, sqlite in-memory
  frontend/   Next.js 14 (App Router) + Tailwind + React Query
  docker-compose.yml
```

## What's built

- **Job discovery** from 4 real, public, documented ATS APIs: Greenhouse, Lever, Ashby,
  SmartRecruiters. These are read-only, unauthenticated job-board endpoints meant for
  third-party consumption — no scraping or ToS violations. LinkedIn, Indeed, Workday
  and company-specific career APIs are **not** implemented; most either require
  partnership agreements or explicitly prohibit unauthenticated automated access.
- **AI match engine** — calls Google Gemini per job/resume pair for a 0–100 score, reasoning,
  missing skills, ATS compatibility, and interview likelihood.
- **Auth** — JWT access/refresh tokens, bcrypt password hashing.
- **Application pipeline** — save → applied → OA → interview → offer → accepted /
  rejected / withdrawn, with an append-only status history for analytics later.
- **Resume storage** (structured JSON, source of truth) and a `Job`/`Company`/
  `Application`/`Document`/`Notification`/`InterviewPrep` schema ready for the features
  below to build on.
- **Dashboard UI** — searchable/filterable job list with the match score shown as a
  radial "signal ring" (see `frontend/DESIGN.md` for the design rationale).
- Docker Compose, Alembic migrations, Celery beat for scheduled syncing, and a real
  pytest suite (auth flow + ATS adapter normalization against mocked HTTP responses).

## What's not built yet

The original brief also asked for: resume/cover-letter AI generation (PDF/DOCX export),
the Playwright application assistant, interview-prep generation, notifications
(email/Slack/Discord/Telegram), analytics dashboards, the AI chat assistant, and 25+
additional ATS/job-board integrations (LinkedIn, Indeed, Workday, Naukri, etc.). The
schema and service layer are structured so each of these is an additive slice rather
than a rewrite — ask and I'll build the next one.

**Note on scope:** none of this code has been run against live dependencies in this
session — the sandbox used to write it has no network access, so `pip install` /
`npm install` couldn't be executed here. All backend files pass a Python syntax check;
review before deploying, and run the test suite yourself once dependencies are
installed.

## Running locally

```bash
cp backend/.env.example backend/.env      # fill in GOOGLE_API_KEY and SECRET_KEY
cp frontend/.env.example frontend/.env.local
docker compose up --build
```

Then, in a separate shell, create tables and seed a few companies:

```bash
docker compose exec backend python -m scripts.init_db
docker compose exec backend python -m scripts.seed_companies
```

Trigger a sync for a company (find its id via `GET /api/v1/companies`):

```bash
curl -X POST http://localhost:8000/api/v1/companies/{company_id}/sync \
  -H "Authorization: Bearer <your access token>"
```

- API docs: http://localhost:8000/docs
- App: http://localhost:3000

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest
```
