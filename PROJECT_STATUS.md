# CareerPilot AI — Full Project Status

161 files. Backend: FastAPI + PostgreSQL + Redis/Celery, clean architecture (repository pattern,
service layer, domain models separate from API schemas). Frontend: Next.js 14 App Router +
Tailwind + React Query. Three sprints of feature work, plus one full verification/hardening pass.

---

## Verification & Hardening Pass (real results — see exact commands below)

The three feature sprints below were originally built in a sandbox with no network access, so
none of `pip install` / `npm install` / `pytest` / `npm run build` had ever actually been run
against them — everything was `py_compile`-clean and logically traced by hand, but unverified.
This pass had real network access and installed everything for real, including standing up
PostgreSQL 16 and Redis 7 directly (Docker itself was not available in this sandbox — no `docker`
binary at all — so `docker-compose.yml` itself remains unverified; everything it would orchestrate
was tested by running the same services directly instead).

### Exact commands run

```bash
# Backend
cd backend && python3 -m venv venv
./venv/bin/pip install -r requirements.txt      # clean, zero conflicts
./venv/bin/python -m pytest -q                  # 38 passed
./venv/bin/python -m py_compile $(find app scripts tests alembic -name "*.py")   # OK
# + a real import test of every module in app/ (not just py_compile)

# Frontend
cd frontend && npm install
npx tsc --noEmit                                # 0 errors
npx next lint                                   # 0 errors (after fixes below)
npm run build                                   # FAILS — see "Known failures" below
npm audit                                       # 1 critical + 4 high -> 0 critical + 4 high after fixes

# Database (Postgres 16 + Redis 7 installed directly via apt, Docker unavailable)
alembic upgrade head        # verified from blank DB
alembic downgrade base      # verified full reversibility
alembic upgrade head        # verified re-upgrade after downgrade (this exposed a real bug — see below)
# + a real reflected-schema-vs-SQLAlchemy-models diff: zero mismatches

# App: ran uvicorn + the actual Next.js dev server against real Postgres/Redis,
# then exercised the API with curl for the flows below.
```

### Bugs found and fixed (all verified against real Postgres/Redis, not assumed)

1. **`db/session.py`** passed `pool_size`/`max_overflow` unconditionally to
   `create_async_engine()`. These are QueuePool-only kwargs; SQLite's async engine (used by the
   whole test suite) uses StaticPool and rejects them — broke every single test at import time.
   Fixed: only pass pooling kwargs for non-SQLite URLs.
2. **Missing dependency**: `EmailStr` (used in auth schemas since Sprint 1) requires
   `email-validator`, never listed in `requirements.txt`. Added, pinned to `2.3.0` (the version
   actually installed and tested).
3. **`passlib==1.7.4` + `bcrypt` incompatibility.** passlib reads `bcrypt.__about__.__version__`,
   removed in bcrypt 4.1+. `requirements.txt` never pinned `bcrypt` directly, so it silently pulled
   5.0.0 — **broke all password hashing** (manifested as a bogus "password too long" error on every
   registration, regardless of actual password length). Pinned `bcrypt==4.0.1`, verified a real
   hash/verify roundtrip.
4. **Alembic `0002_resume_intelligence.py` could not run against a fresh Postgres database at
   all.** It called `op.add_column(..., sa.Enum(...))` on an existing table; unlike
   `op.create_table()` (which auto-creates Postgres enum types as a side effect),
   a bare `add_column()` only references the type by name and fails if it doesn't exist yet.
   Reproduced against a real Postgres 16 instance. Fixed: explicitly create the enum type first.
5. **Alembic `0001_initial_schema.py`'s `downgrade()` didn't drop the Postgres enum types it
   created**, only the tables. `op.drop_table()` does not cascade to enum types (separate catalog
   objects). This broke `downgrade → upgrade` reversibility with "type already exists" — reproduced
   live. Fixed: explicitly drop all 7 enum types in `downgrade()`.
6. **The most serious bug found**: every SQLAlchemy `Enum`-typed column across **10 locations in 5
   model files** (`job.py`, `application.py`, `resume.py`, `user.py`, `notification.py`) was
   serializing the Python enum member's `.name` ("GREENHOUSE") instead of `.value` ("greenhouse"),
   while the Alembic migrations created native Postgres enum types containing only the lowercase
   `.value`s. **Every write to any enum column would have failed against real production
   Postgres** — completely invisible in all 30 (then 38) passing tests because SQLite never
   enforces this the way Postgres's native enum type does. Fixed by adding
   `values_callable=lambda x: [e.value for e in x]` to all 10 columns; verified with a real
   write-then-read-back round-trip against Postgres.
7. **Rate limiter's module-level Redis client singleton broke across asyncio event loops** —
   `redis.asyncio`'s client ties its connection to whichever event loop is running when it first
   sends a command. Invisible in every earlier test run because Redis was unreachable (fail-open
   path taken immediately, real connection never established); surfaced the moment real Redis
   became available, as "Future attached to a different loop" errors across sequential pytest
   tests. This is also a **real production risk**, not just a test artifact: this project's own
   Celery tasks (`tasks/job_sync.py`, `tasks/resume_processing.py`) call `asyncio.run()` per task
   invocation, which creates a fresh event loop every time — the exact pattern that triggers this
   bug. Fixed: create a short-lived Redis client per call instead of caching a singleton.
8. **All 6 AI-calling services** (`MatchingService`, `ResumeParserService`,
   `ResumeAnalysisService`, `ResumeCustomizationService`, `CoverLetterService`,
   `InterviewPrepService`) never caught Anthropic API errors — an invalid key, rate limit, or
   outage all leaked through as generic, unhelpful 500s. Discovered live: uploading a real PDF
   resume with a placeholder API key returned a raw 500. The `jobs.py` match endpoint didn't even
   have a try/except around the service call at all. Fixed consistently across all 6 services plus
   the match endpoint; verified live that the same request now returns a clear, specific error
   instead.
9. **`JobRepository.search()` pagination** — confirmed the issue flagged in the prior status
   report was still real: it loaded every matching row into Python and paginated by list-slicing.
   Rewrote to real DB-level `LIMIT`/`OFFSET` with a proper `COUNT` subquery, and added an explicit
   `ORDER BY` (pagination had none before — a related, previously-unnoticed correctness gap, since
   row order across pages was technically undefined). Verified two ways: live against Postgres
   with 5 seeded jobs (correct page splits, totals, no dupes/gaps), and 4 new pytest tests against
   the exact rewritten code.
10. **Frontend security**: `npm audit` flagged Next.js 14.2.15 with 1 critical + 4 high CVEs
    (DoS, SSRF, cache poisoning, XSS). Did **not** run `npm audit fix --force` (which jumps to the
    breaking Next 16 major version). Instead bumped to `14.2.35` (latest patch in the *same* minor
    line) and pinned `postcss` to `8.5.26` via an `overrides` block (both our direct pin and Next's
    internally-bundled copy were vulnerable). This resolved the critical and all postcss CVEs.
    **4 high-severity CVEs remain** — npm's advisory ranges for these specifically cover the entire
    14.x/15.x lines with no backported patch; fully resolving them requires a major-version
    migration to Next 16, a real, separate, scoped effort, not something to force during a
    hardening pass.
11. **Frontend: `eslint-config-next` was still pinned to `14.2.15`** (unpatched) even after
    bumping `next` itself — fixed to `14.2.35` to match.
12. **4 real ESLint errors** (`react/no-unescaped-entities` — raw apostrophes in JSX across 4
    pages) plus a **missing ESLint config entirely** (`npm run lint` had nothing to run against).
    Added `.eslintrc.json`, fixed all 4.
13. **Frontend: 5 pages had no `isError` handling** for their main data fetch
    (`/applications`, `/resumes`, `/resumes/[id]`, `/applications/[id]`) — a failed request left
    the user on an infinite loading state or a silent blank screen with zero feedback. Fixed all 4
    (the 5th, `/dashboard`, already had this).
14. **Frontend: no auth-guard on any protected page.** Only the root `/` page checked for a token
    before this; `/dashboard`, `/resumes`, `/resumes/[id]`, `/applications`, `/applications/[id]`
    would render normally for an unauthenticated user and just silently 401 on every API call
    instead of redirecting to `/login`. Added a shared `useRequireAuth()` hook, wired into all 5.
    **Caveat**: this fix could only be verified by code review and TypeScript/lint checks — it's a
    `useEffect`-driven client-side redirect, invisible to `curl`, and no real browser was available
    in this sandbox to click through it.
15. **Frontend: misleading UI copy.** `ExportButtons.tsx` told users to "see Documents list" after
    a successful export — no such page exists anywhere in the app. Fixed the copy; did not build
    the documents-list page itself (see "Confirmed UI gaps" below).
16. Minor: deprecated Pydantic v1-style `class Config` in `companies.py` (inconsistent with
    `ConfigDict` used everywhere else) and a pytest-asyncio deprecation warning — both fixed for
    consistency/future-proofing, not functional bugs.

### Confirmed UI gaps (found, not fixed — genuinely new feature surface, not hardening)

- **Resume customization has no UI.** `POST /resumes/{id}/customize` and its frontend hook
  (`useCustomizeResume`) both exist and work, but no page or button anywhere calls it. A user
  cannot tailor a resume for a job through the app today.
- **Cover letter generation has no UI.** Same situation — `useGenerateCoverLetter` exists, nothing
  calls it.
- **No documents list page** — exported/generated files exist in the database and on disk
  (verified: real PDF/DOCX files, correctly downloadable via `GET /documents/{id}` with correct
  ownership checks) but there's no page to browse them.

These were deliberately not built during this pass — they're real feature gaps, not defects in
existing code, and building them is Sprint-4-adjacent scope rather than verification/hardening.

### What was verified live, end-to-end, against real infrastructure

- **Auth**: register, duplicate-409, login, wrong-password-401, unauthenticated-401, authenticated
  `/users/me`, refresh — all correct.
- **IDOR/ownership protection**: a second "attacker" user gets a clean 404 (not 403, not a leak) on
  both `GET` and `PATCH` of another user's application and another user's document; their own
  pipeline summary correctly shows no data. Verified with a fresh token after a mid-session sandbox
  reset invalidated the first attempt, rather than assuming the ambiguous result was fine.
- **Applications**: create, retrieve, status transition, pipeline summary.
- **Resume upload validation**: invalid MIME type → 415, oversized file (6MB against a 5MB limit)
  → 413, empty file → 400. Real PDF text extraction (via `pypdf`) confirmed working — the only
  failure in that path was the external Anthropic call itself (expected: placeholder API key).
- **Resume export**: PDF and DOCX both produce real, valid files on disk (confirmed with `file`,
  not just a 201 response).
- **Rate limiting**: live-tested against real Redis — 20 requests to `/resumes/{id}/analyze`
  succeeded (or correctly 409'd for business-logic reasons), the 21st correctly returned 429.
- **Job pagination**: 5 seeded jobs, page size 2 → pages of 2/2/1, correct totals, no
  duplicates/gaps across pages.
- **Migrations**: `0001 → 0002` upgrade, full downgrade to base, and re-upgrade all verified
  against real Postgres 16, including a genuine schema-vs-model diff (zero mismatches).

### Known failures / external dependencies that could not be tested

- **`npm run build` fails in this sandbox.** Next.js fetches Google Fonts CSS at build time;
  `fonts.googleapis.com` and `fonts.gstatic.com` both return 403 here (confirmed via direct
  `curl`, while an allowed domain like `pypi.org` returns 200 normally) — this sandbox's network
  allowlist doesn't include Google's font CDN. `next dev` degrades gracefully (falls back to a
  system font, pages still render 200) — only the production build treats it as fatal. This is a
  real dev/prod asymmetry worth knowing about, and a real risk for any CI environment with
  restricted egress, but is very likely sandbox-specific rather than something that will reproduce
  in a normal deployment pipeline with standard internet access. **`tsc --noEmit` and `next lint`
  both pass with zero errors**, independent of this build blocker.
- **Docker was not available in this sandbox at all** (no `docker` binary). `docker-compose.yml`
  itself was never actually run — its service definitions, networking, and volume configuration
  remain unverified. Substituted by installing Postgres 16 and Redis 7 directly via apt and running
  every service `docker-compose.yml` defines (backend, celery_worker, celery_beat) directly against
  them instead — all 5 processes (Postgres, Redis, FastAPI app, Celery worker, Celery beat)
  confirmed running **simultaneously** via `ps aux`. The Celery worker was verified for real, not
  just by checking it started: submitted an actual task (`sync_single_company.delay(...)`) through
  the real Redis broker, waited on `.get()` for the real result via the Redis result backend, and
  confirmed in the worker's own log that it executed the full task body — including a real
  `tenacity` retry sequence against the (network-blocked) Greenhouse API, caught gracefully by
  `JobDiscoveryService`, task reported `SUCCESS` with the correct error-stats dict. Celery beat
  was confirmed running and correctly loaded its configured hourly schedule
  (`sync-all-companies`) without crashing. The full pytest suite (38/38) was also re-run with this
  entire stack live simultaneously, as the most realistic verification possible without Docker
  itself.
- **Live ATS sync (Greenhouse/Lever/Ashby/SmartRecruiters) could not be tested against the real
  internet** — those domains aren't in this sandbox's network allowlist either (confirmed via
  curl, same 403 pattern as the fonts issue). The sync path's error handling was verified working
  correctly in this exact failure mode (caught, logged, returned gracefully as HTTP 202 with an
  error count, did not crash) — and is separately covered by 4 new mocked pytest tests exercising
  the idempotency logic Phase 5 specifically asked about (duplicate sync doesn't duplicate,
  updates apply, deactivation works, adapter failures are caught).
- **Real AI generation (Claude calls) could not be tested end-to-end** — no real
  `ANTHROPIC_API_KEY` was available (a placeholder was used, correctly producing 401s from
  Anthropic). This is exactly the "external dependency requiring credentials" case: matching,
  resume analysis/customization, cover letters, and interview prep are all covered by mocked
  integration tests instead (which pass), and the *error-handling path* for AI failures was
  verified live and for real (see bug #8 above).
- **The `useRequireAuth()` client-side redirect fix could not be click-tested in a real browser**
  — no browser is available in this sandbox. Verified by code review, pattern-consistency with the
  already-proven root-page redirect, and a clean TypeScript/lint pass only.

### Test count: **38 passing**, up from 30 (8 new tests added, all targeting real, previously-
uncovered risks explicitly called out during this pass — none added to pad the count)

---



## Sprint 1 — Core Platform + Job Discovery

**Goal:** discover real jobs from public ATS APIs, score fit with Claude, track pipeline status.

### Domain models (`backend/app/domain/models/`)
- `User` — auth fields, profile (GitHub/LinkedIn/portfolio URLs, work authorization, salary
  preference, notice period)
- `Company` — name/slug/website, `ats_provider` + `ats_identifier` (which ATS + board token)
- `Job` — normalized posting regardless of source ATS; `external_id` + `ats_provider` unique
  together so re-syncing never duplicates
- `JobMatchScore` — cached AI match result per (job, user, resume)
- `Application` + `ApplicationStatusHistory` — pipeline state machine with an append-only audit
  trail (saved → applied → oa → interview → offer → accepted/rejected/withdrawn)
- `Resume`, `Document`, `Notification`, `InterviewPrep` — defined in Sprint 1, mostly unused until
  later sprints filled in the services around them

### ATS adapters (`backend/app/services/ats_adapters/`)
Real, public, documented, unauthenticated job-board APIs — no scraping, no ToS violations:
- **Greenhouse** (`boards-api.greenhouse.io`)
- **Lever** (`api.lever.co/v0/postings`)
- **Ashby** (`api.ashbyhq.com/posting-api`)
- **SmartRecruiters** (`api.smartrecruiters.com`)

Each implements `BaseATSAdapter.fetch_postings()` → returns `NormalizedPosting` DTOs. A
`factory.py` maps `ATSProvider` enum → adapter class. **Not implemented:** LinkedIn, Indeed,
Workday, Naukri, and direct company career-page APIs — most require partnership agreements or
explicitly disallow unauthenticated automated access.

### Services
- `JobDiscoveryService` — idempotent sync: upserts postings by `(company_id, ats_provider,
  external_id)`, deactivates postings that disappeared upstream
- `MatchingService` — calls Claude for a strict-JSON match score (0–100), reasoning, missing
  skills, ATS compatibility, interview likelihood, difficulty
- `AuthService` — JWT access/refresh tokens, bcrypt hashing

### API (`/api/v1`)
`POST /auth/register|login|refresh`, `GET/PATCH /users/me`, `GET /jobs`, `GET /jobs/{id}`,
`POST /jobs/{id}/match`, `GET/POST /applications`, `PATCH /applications/{id}/status`,
`GET /applications/pipeline-summary`, `GET/POST /resumes`, `DELETE /resumes/{id}`,
`GET/POST /companies`, `POST /companies/{id}/sync`

### Infrastructure
Celery + Redis for scheduled job sync (`tasks/job_sync.py`, hourly beat schedule), Docker Compose
(Postgres, Redis, backend, celery_worker, celery_beat, frontend), cross-dialect `GUID` type so
tests run on SQLite without a real Postgres instance.

### Frontend
Dark "instrument panel" design system (`DESIGN.md` — Space Grotesk/Inter/JetBrains Mono, signal
ring match-score gauge as the signature visual element). Pages: `/`, `/login`, `/register`,
`/dashboard` (job search/filter, match scoring). Components: `Navbar`, `JobCard`, `MatchGauge`.

### Tests
`test_auth.py` (register/login/duplicate/auth-required flows), `test_ats_adapters.py` (Greenhouse
+ Lever normalization against mocked HTTP responses).

---

## Sprint 2 — Resume Intelligence + Cover Letter AI

**Goal:** upload/parse resumes, AI-analyze them, tailor per job, export, generate cover letters —
with a hard guarantee against fabricated experience.

### What changed on `Resume`
Added (additive, non-breaking): `version`, `parent_resume_id` (lineage — tailored variants are new
rows, never overwrites), `source_file_path`, `parse_status` (pending/parsed/failed). `content` is
now validated against a real `ResumeContent` Pydantic schema (contact, summary, skills, experience,
education, projects, achievements, languages) instead of an untyped dict.

### New model
- `ResumeAnalysis` — cached standalone AI analysis (ATS score, extracted skills, strengths,
  weaknesses, optional missing-skills-by-target-role)

### The fabrication guard (`services/fabrication_guard.py`)
The core safety mechanism for this sprint. `check_for_fabrication()` compares AI-generated content
against every word in the source resume and flags capitalized tokens (candidate proper nouns —
companies, schools, technologies) that don't appear anywhere in the source. This is a **real
post-generation check**, not just a prompt instruction — both `ResumeCustomizationService` and
`CoverLetterService` call it before persisting anything, and reject with a 422 naming the specific
flagged terms if it fires. Disclosed limitation: it's a heuristic (word-presence check), not a
semantic proof.

### Services
- `ResumeParserService` — extracts text locally (pypdf for PDF, python-docx for DOCX), then a
  Claude call with a strict "transcribe only, never invent" prompt structures it into
  `ResumeContent`
- `ResumeAnalysisService` — ATS score, skill extraction, strengths/weaknesses, optional
  target-job-specific missing skills
- `ResumeCustomizationService` — reorders/reweights existing content for a target job; output run
  through the fabrication guard before being saved as a new versioned `Resume` row
- `CoverLetterService` — personalized, company/role-specific; same fabrication guard (with the
  target company name and role title explicitly allow-listed, since those are legitimately new
  terms in a cover letter)
- `DocumentExportService` — pure formatting, no AI: resume/cover-letter → PDF (reportlab) and DOCX
  (python-docx), single-column and ATS-friendly by design
- `StorageService` — `StorageBackend` interface + `LocalFileStorage` implementation, path-traversal
  protected, structured to swap in S3 later without touching callers

### New infrastructure
- `require_owner()` — shared 404-on-mismatch ownership check (`api/deps.py`), used by every new
  endpoint below
- `check_rate_limit()` — Redis-backed per-user-per-bucket limiter (`core/rate_limit.py`), **fails
  open** if Redis is unreachable (logs a warning, allows the request) so a Redis outage doesn't
  take down AI endpoints entirely
- Celery tasks `parse_resume_task`, `analyze_resume_task` — built and registered, but **not** wired
  into the default request flow (see Deviations below)
- Alembic migrations: `0001_initial_schema` (the *first* real migration — Sprint 1 had only
  `create_all` for dev) and `0002_resume_intelligence` (additive-only, safe against existing data)

### API additions
`POST /resumes/upload`, `GET /resumes/{id}`, `GET /resumes/{id}/versions`,
`POST /resumes/{id}/analyze`, `GET /resumes/{id}/analysis`, `POST /resumes/{id}/customize`,
`POST /resumes/{id}/export`, `POST /applications/{id}/cover-letter`, `GET /documents/{id}`

### Deviation from the approved design (disclosed at the time)
Design proposed `202 Accepted` + polling for upload/analyze via Celery. Shipped as **synchronous**
endpoints instead, matching Sprint 1's own convention (`POST /jobs/{id}/match` is sync). The Celery
tasks exist and are registered, so switching to async-with-polling later is additive, not a rewrite.

### Frontend
`/resumes` list page + `ResumeUploadDropzone`, `/resumes/[id]` detail page (ATS score via the same
`MatchGauge` component reused from Sprint 1, extracted skills, strengths/weaknesses, export
buttons). New components: `ResumeUploadDropzone`, `SkillTagList`, `ExportButtons`. New hooks file
`lib/resumes.ts`.

### Tests
`test_fabrication_guard.py` (the highest-value test in this sprint — proves it catches invented
companies/skills and doesn't false-positive on legitimate restatement or lowercase prose),
`test_storage_service.py` (roundtrip, nested dirs, missing-file, delete, **path traversal
rejection**), `test_resume_intelligence.py` (create/analyze/export flows, ownership 404, malformed
AI response handling, upload MIME/size rejection).

---

## Sprint 3 — Interview Preparation

**Goal:** generate company summary, current news, likely interview rounds, and tailored practice
questions per application.

### The one deliberate live-web-search call in the app
`InterviewPrepService.fetch_latest_news()` uses Claude's server-side `web_search_20250305` tool.
Everywhere else in the app, Claude answers from its own knowledge (job/resume matching, analysis,
customization) — this is the one place where "latest news" specifically demands something a
training cutoff can't provide. If web search fails or is unavailable, it fails soft (empty news
list), not hard — generation still proceeds.

### Service
`InterviewPrepService` — two calls: (1) web-search news fetch, (2) strict-JSON generation of
company summary, tech stack, likely rounds, and 7 question categories (behavioral, coding, system
design, frontend, LLD, HLD — the prompt is told to skip categories that wouldn't realistically
apply, e.g. no system design questions for an entry-level role).

### Repository
`InterviewPrepRepository.upsert()` — `InterviewPrep.application_id` has a unique constraint from
Sprint 1's original model, so regeneration overwrites in place rather than versioning (prep isn't
meant to be a history the way resumes are).

### API additions
`POST /applications/{id}/interview-prep` (generate/regenerate; `force_refresh_news` flag — off by
default, so regenerating reuses cached news and only re-runs the fast strict-JSON call, not the
slow web search), `GET /applications/{id}/interview-prep`.

### Gap found and fixed while building this
**The application pipeline had a working API since Sprint 1 but zero frontend.** Fixed:
- `GET /applications/{id}` — didn't exist; added, registered *after* the existing static
  `/pipeline-summary` route specifically to avoid the dynamic `/{id}` path shadowing it
- `/applications` page — pipeline list grouped by status
- `/applications/[id]` page — detail view with the full interview prep panel
- `JobCard` gained a "Save" button (`onSaveToPipeline` prop) wired to `POST /applications` — without
  it, the new pipeline pages were unreachable from the main dashboard flow

### Tests
`test_interview_prep.py` — generation with both AI calls mocked, cached-news-reuse-on-regenerate
(asserts only 1 call happens instead of 2), ownership 404, 404-before-first-generation, and the
web-search-failure-doesn't-block-generation path.

---

## Full file tree (154 files)

```
careerpilot-ai/
├── CHANGELOG.md                          # detailed, chronological, includes self/arch/security/perf review per sprint
├── README.md
├── docker-compose.yml                    # db, redis, backend, celery_worker, celery_beat, frontend
├── backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 0001_initial_schema.py        # Sprint 1's schema (first real migration)
│   │       └── 0002_resume_intelligence.py   # additive-only
│   ├── scripts/
│   │   ├── init_db.py                    # dev convenience: create_all
│   │   └── seed_companies.py             # real ATS identifiers (Stripe, Airbnb, Netflix, etc.)
│   ├── app/
│   │   ├── main.py                       # FastAPI app, CORS, exception handler, /health
│   │   ├── core/
│   │   │   ├── config.py                 # Settings (env-driven), storage/rate-limit config
│   │   │   ├── security.py               # JWT issue/verify, bcrypt
│   │   │   ├── celery_app.py             # Celery + beat schedule
│   │   │   └── rate_limit.py             # Redis fixed-window limiter, fails open
│   │   ├── db/
│   │   │   ├── base.py                   # declarative Base, GUID cross-dialect type, TimestampMixin
│   │   │   └── session.py                # async engine/session factory
│   │   ├── domain/
│   │   │   ├── models/                   # SQLAlchemy ORM: user, company, job, application,
│   │   │   │                             # resume, notification, interview_prep
│   │   │   └── schemas/                  # Pydantic: auth, user, job, application, resume,
│   │   │                                 # interview_prep
│   │   ├── repositories/                 # base + user, company, job, application, resume,
│   │   │                                 # document, interview_prep
│   │   ├── services/
│   │   │   ├── ats_adapters/             # base, greenhouse, lever, ashby, smartrecruiters, factory
│   │   │   ├── auth_service.py
│   │   │   ├── job_discovery_service.py
│   │   │   ├── matching_service.py
│   │   │   ├── resume_parser_service.py
│   │   │   ├── resume_analysis_service.py
│   │   │   ├── resume_customization_service.py
│   │   │   ├── cover_letter_service.py
│   │   │   ├── fabrication_guard.py
│   │   │   ├── document_export_service.py
│   │   │   ├── storage_service.py
│   │   │   └── interview_prep_service.py
│   │   ├── api/
│   │   │   ├── deps.py                   # CurrentUser, DbSession, require_owner
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/            # auth, users, jobs, applications, resumes,
│   │   │                                 # resume_intelligence, interview_prep, companies
│   │   └── tasks/                        # job_sync, resume_processing (Celery)
│   └── tests/
│       ├── conftest.py                   # in-memory SQLite fixtures, async client
│       ├── test_auth.py
│       ├── test_ats_adapters.py
│       ├── test_fabrication_guard.py
│       ├── test_storage_service.py
│       ├── test_resume_intelligence.py
│       └── test_interview_prep.py
└── frontend/
    ├── .env.example / Dockerfile / package.json / tsconfig.json / tailwind.config.ts / postcss.config.js
    ├── DESIGN.md                          # design system rationale
    ├── app/
    │   ├── layout.tsx / providers.tsx / globals.css / page.tsx (root redirect)
    │   ├── login/, register/              # auth pages
    │   ├── dashboard/                     # job search/filter/match/save
    │   ├── resumes/, resumes/[id]/        # upload, list, analysis, export
    │   └── applications/, applications/[id]/  # pipeline list, detail + interview prep panel
    ├── components/
    │   ├── Navbar, JobCard, MatchGauge
    │   └── ResumeUploadDropzone, SkillTagList, ExportButtons
    └── lib/
        ├── api.ts (fetch wrapper), types.ts, auth.ts, resumes.ts, applications.ts
```

---

## What is NOT built yet

From the original brief, still outstanding:
- **Notifications** — email/Slack/Discord/Telegram, daily/weekly summaries. `Notification` model
  exists from Sprint 1, nothing else does.
- **Analytics dashboards** — applications/week, response rate, interview rate, offer rate, salary
  trends, heatmaps. No model, no service, no UI.
- **AI chat assistant** — "should I apply?", "negotiate salary", etc. Not started.
- **Playwright application assistant** — auto-fill/submit applications. Not started; this is also
  the highest-risk feature from a ToS/safety standpoint and would need careful scoping.
- **~25 additional job sources** — LinkedIn, Indeed, Workday, Naukri, Instahyre, and direct
  company career APIs. Deliberately excluded so far — most require partnership access or forbid
  unauthenticated automation.
- **Common-questions auto-answer** (why us, expected salary, notice period, etc. as a distinct
  feature from cover letters) — not started.

## Known gaps / honest weak spots in what *is* built
- ~~`JobRepository.search()` loads all matching rows into Python~~ — **fixed during the
  verification pass**: now real DB-level `LIMIT`/`OFFSET` with a proper `COUNT` subquery.
- Resume/analysis/customization/cover-letter/interview-prep endpoints are all synchronous within
  the request — fine at current scale, first place to move to the already-built Celery tasks if
  AI-endpoint latency becomes a problem under load. Confirmed intentional, not revisited.
- The fabrication guard is a word-presence heuristic, not a semantic fact-checker.
- **Resume customization and cover letter generation have no frontend UI** — confirmed during the
  verification pass (see above). The backend works; nothing in the app lets a user trigger it.
- **No documents list page** — exported files exist and are correctly downloadable by ID, but
  aren't browsable anywhere in the UI.
- **4 unresolved high-severity npm CVEs** in the Next.js 14.x/15.x line that require a major-version
  migration to Next 16 to fully resolve — a deliberate, scoped follow-up, not fixed in this pass.
- **`npm run build` cannot be verified in this sandbox** due to a blocked Google Fonts dependency
  at build time (see Verification & Hardening Pass section above for full detail) — very likely
  sandbox-specific, but unverified in a real build environment.
- **Docker Compose itself has never been run** — Docker wasn't available in this sandbox at all.
  The app was verified against real Postgres/Redis installed directly instead, which validates the
  application code but not the Compose file's service/network/volume definitions.
- One major class of bug (SQLAlchemy enum serialization mismatch — see Verification section) was
  completely invisible across 30 passing tests because SQLite doesn't enforce Postgres-style native
  enum constraints. This is now fixed and verified, but is a reminder that "tests pass on SQLite"
  and "works on production Postgres" are not the same claim for this stack.
