# Changelog

All notable changes to CareerPilot AI are tracked here.

## AI Provider Migration: Anthropic → Google Gemini (complete)

### Why
Anthropic is no longer the required AI provider; Google Gemini is now primary. The migration
introduced a real `LLMProvider`/`GeminiProvider`/`LLMRouter` abstraction so no individual service
depends on a specific vendor's SDK directly — a future second provider is a config change, not a
rewrite.

### Added
- `backend/app/services/llm/` — `LLMProvider` (interface), `LLMResponse`, `LLMError`/
  `LLMUnavailableError`/`LLMMalformedResponseError`, `GeminiProvider`, `LLMRouter`
- `GeminiProvider` built against the real, currently-installed `google-genai==2.20.0` SDK — API
  surface (async client, JSON mode, search grounding, error hierarchy, usage metadata field names)
  verified by installing the package and inspecting it directly, not assumed from documentation
- **Real, confirmed Gemini API constraint** (found via research, not assumption): `json_mode` and
  `use_web_search` cannot be combined in a single call — Gemini rejects
  `response_mime_type="application/json"` combined with `tools` with a 400 error. `GeminiProvider`
  now raises a clear `LLMError` if both are requested together, and `InterviewPrepService` (the one
  caller needing both) correctly makes two separate calls, same as it always did
  (`fetch_latest_news` with search grounding, then `generate_prep` with JSON mode)
- Lightweight LLM call telemetry via structured logging in `LLMRouter` (provider, model, latency,
  success/failure, token counts) — no new database table, no prompt content ever logged
- `tests/test_llm_router.py` — 8 new tests covering provider selection, error propagation, the
  `json_mode`+`use_web_search` guard, and Gemini-specific error mapping (API errors, network
  errors) verified against the real SDK's exception types

### Changed
- All 6 AI-calling services (`MatchingService`, `ResumeParserService`, `ResumeAnalysisService`,
  `ResumeCustomizationService`, `CoverLetterService`, `InterviewPrepService`) migrated from direct
  `AsyncAnthropic` usage to `LLMRouter` — each now accepts an optional `router` constructor param
  for test injection, defaulting to the real router
- `config.py`: `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` → `LLM_PROVIDER` (default `gemini`),
  `GOOGLE_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`)
- `requirements.txt`: `anthropic==0.34.2` → `google-genai==2.20.0`. Installing this fresh surfaced
  2 real dependency conflicts, both fixed with the minimum version satisfying the actual
  constraint (verified via `pip check`, not guessed): `httpx` `0.27.2` → `0.28.1`, `pydantic`
  `2.9.2` → `2.12.5`
- `backend/.env.example`, `render.yaml`, `.github/workflows/ci.yml`, `backend/tests/conftest.py`:
  `ANTHROPIC_API_KEY` → `GOOGLE_API_KEY` (the CI workflow change matters — the migrated code no
  longer reads `ANTHROPIC_API_KEY` at all, so CI would have silently broken without this)
- 6 test mock sites across `test_resume_intelligence.py`/`test_interview_prep.py` rewritten to
  mock at the `LLMRouter` seam (`app.services.llm.router.get_provider`) instead of per-service
  `AsyncAnthropic` patches — the abstraction made this simpler: one patch point covers every
  service uniformly instead of six separate ones
- `README.md`, `DEPLOYMENT.md`: Claude/Anthropic → Gemini. `DEPLOYMENT.md` also had accumulated
  staleness unrelated to the provider swap that got fixed while in there: still described creating
  Celery worker/beat services (removed earlier — free tier doesn't support them) and using the
  Shell tab for migrations/seeding (also unavailable on free tier — migrations now run
  automatically via `start.sh`, seeding now documented via the real `POST /companies` API endpoint
  instead)
- Historical `CHANGELOG.md`/`PROJECT_STATUS.md` entries describing Sprint 1–3 and the verification
  pass are left untouched — they're an accurate record of decisions made with Anthropic at the
  time, not something to retroactively rewrite

### Verified
- `pip check`: no broken requirements after the dependency bumps
- Real import check: every module in `app/` imports successfully with `google-genai` installed
- Full test suite: 55/55 passing (was 47) — 6 fixed, 8 added, 0 broken
- Full-repo grep confirms zero remaining functional Anthropic references (the only matches left
  are historical changelog/status entries, a seed-data company literally named "Anthropic", and
  comments explaining the migration itself)

### Known limitation
- **A real, live call to the Gemini API could not be made from the development sandbox** —
  `generativelanguage.googleapis.com` isn't in that sandbox's network allowlist (same restriction
  pattern as Google Fonts and the ATS provider APIs hit earlier in this project). Got as far as a
  real, well-formed request reaching Google's servers and receiving a structured error back
  (confirming the SDK usage is correctly formed), but never a full successful round-trip with real
  content. This needs to be the first thing verified once a real `GOOGLE_API_KEY` is set in the
  actual deployment.

---

## Verification & Hardening Pass (complete)

Real installation, real Postgres/Redis, real test runs — see `PROJECT_STATUS.md`'s "Verification
& Hardening Pass" section for full detail, exact commands, and what remains unverified (Docker
itself, `npm run build`, live ATS/AI network calls). Summary:

### Fixed
- `db/session.py`: pool kwargs incompatible with SQLite, broke every test
- Missing `email-validator` dependency (required by `EmailStr`, never listed)
- `bcrypt` pinned to `4.0.1` — `passlib==1.7.4` is incompatible with `bcrypt>=4.1`, which broke **all** password hashing
- Alembic `0002`: didn't create its Postgres enum type before referencing it — migration could not run against a fresh database at all
- Alembic `0001`: `downgrade()` didn't drop its enum types — broke upgrade/downgrade/upgrade reversibility
- **10 SQLAlchemy `Enum` columns across 5 model files** serialized `.name` instead of `.value`, mismatching the migrations' lowercase-only Postgres enum types — every enum-column write would have failed against real production Postgres; invisible in all tests because SQLite doesn't enforce this the way Postgres does
- Rate limiter's Redis client singleton broke across asyncio event loops — a real production risk given the Celery tasks' `asyncio.run()`-per-call pattern, not just a test artifact
- All 6 AI-calling services now catch `anthropic.APIError` and raise a proper domain exception instead of leaking generic 500s; `jobs.py`'s match endpoint previously caught nothing from `MatchingService` at all
- `JobRepository.search()`: rewritten from in-Python list-slicing to real DB-level `LIMIT`/`OFFSET` + `COUNT` subquery + explicit `ORDER BY` (this exact issue was flagged as a known risk in the prior status report — confirmed still real, now fixed)
- Frontend: Next.js `14.2.15` → `14.2.35` (patched a critical DoS CVE + postcss XSS CVE within the same minor line, no forced major upgrade), `eslint-config-next` bumped to match, `postcss` pinned to `8.5.26` via `overrides`
- Frontend: added missing `.eslintrc.json`, fixed 4 real `react/no-unescaped-entities` errors
- Frontend: added `isError` handling to 4 pages that previously left users on an infinite loading state or blank screen on fetch failure
- Frontend: added `useRequireAuth()` guard to all 5 protected pages — previously only the root `/` page checked for a token
- Frontend: fixed misleading copy in `ExportButtons.tsx` referencing a "Documents list" page that doesn't exist
- Minor: deprecated Pydantic v1-style `Config` class in `companies.py`, pytest-asyncio deprecation warning

### Added (tests only — 30 → 38)
- `test_job_discovery_service.py` — duplicate sync doesn't duplicate jobs, field updates apply, deactivation of disappeared postings, graceful handling of adapter failures
- `test_job_repository_pagination.py` — covers the rewritten pagination logic, which had zero prior test coverage

### Verified (infrastructure, no code changes needed)
- Docker itself unavailable in this sandbox (no `docker` binary) — substituted by running every service `docker-compose.yml` defines (Postgres 16, Redis 7, FastAPI app, Celery worker, Celery beat) directly, all 5 confirmed running simultaneously
- **Celery worker**: verified for real, not just process-started — submitted an actual task through the real Redis broker, waited on the real result via the Redis result backend, confirmed in the worker's log it executed the full task body including a real `tenacity` retry sequence, caught gracefully, task reported `SUCCESS`
- **Celery beat**: confirmed running, correctly loaded its configured hourly schedule without crashing
- Full pytest suite (38/38) re-run with the entire stack live simultaneously

### Found but not fixed (confirmed real gaps, deliberately out of scope for a hardening pass)
- Resume customization and cover letter generation have working backends but **no frontend UI** calls them anywhere
- No documents list page in the frontend
- 4 high-severity npm CVEs remain, require a Next.js 16 major-version migration to fully resolve
- `npm run build` fails in this sandbox specifically (blocked Google Fonts network access at build time) — `next dev`, `tsc --noEmit`, and `next lint` all pass
- Docker was never actually run (unavailable in this sandbox) — substituted real Postgres/Redis installs

---

## Sprint 3 — Interview Preparation (complete)

### Added
- `InterviewPrepService` — two Claude calls: (1) `fetch_latest_news` using the server-side `web_search_20250305` tool (the one place in the app that does a live search, since "latest news" goes stale from training data alone), (2) `generate_prep`, a strict-JSON call producing company summary, tech stack, likely rounds, and 7 question categories, grounded in the job description + real news
- `InterviewPrepRepository` — upsert semantics (`InterviewPrep.application_id` has a unique constraint; regeneration overwrites in place rather than versioning, since prep material isn't meant to be a history the way resumes are)
- API: `POST /applications/{id}/interview-prep` (generate/regenerate, `force_refresh_news` flag to control whether the web-search call re-runs), `GET /applications/{id}/interview-prep`
- API: `GET /applications/{id}` — was missing; the dashboard could list applications but never fetch one, so the new detail page needed it. Registered *after* the existing static `/pipeline-summary` route to avoid the dynamic `/{id}` path shadowing it.
- Frontend: `/applications` pipeline list page (grouped by status) and `/applications/[id]` detail page with the full interview prep panel — **these didn't exist before**; Sprint 1 built the pipeline API but the frontend never rendered it
- Frontend: `JobCard` gained a "Save" action wired to `POST /applications`, since without it the new pipeline pages were unreachable from the main flow
- Tests: `test_interview_prep.py` — generation, cached-news reuse on regenerate, ownership (404), and the web-search-failure-doesn't-block-generation path

### Changed
- Nothing in Sprint 1 or Sprint 2 modified — this sprint only added new files and two small, additive endpoints (`GET /applications/{id}`) and props (`JobCard`'s new optional `onSaveToPipeline`)

### No migration needed
`interview_preps` table already existed in `0001_initial_schema` — the model was defined in Sprint 1 but never used until now.

### Self/Architecture/Security/Performance Review
- **Self-review:** all files pass `py_compile`; frontend brace-matching clean; no TODO/FIXME left in application code. Same standing caveat as Sprints 1–2: no network in this sandbox, so `pytest`/`npm install` were not actually executed here — the web-search mock tests were traced by hand (call-count assertions, side-effect ordering) but should be run for real before trusting them in CI.
- **Architecture:** reuses `ApplicationRepository.get_for_user`, `check_rate_limit`, and the same strict-JSON Claude contract pattern established in `MatchingService`/`ResumeAnalysisService` — no new conventions introduced.
- **Security:** ownership enforced via `ApplicationRepository.get_for_user` (scoped by `user_id`, returns 404 not 403, consistent with `require_owner` elsewhere); rate-limited via the same Redis fail-open limiter from Sprint 2.
- **Performance:** the web-search call is the slowest part of this flow and is now cached — a regenerate only re-runs the (fast) strict-JSON call unless `force_refresh_news` is explicitly set, avoiding a redundant search on every prep refresh.

---

## Sprint 2 — Resume Intelligence + Cover Letter AI (complete)

### Added
- `Resume.version`, `Resume.parent_resume_id`, `Resume.source_file_path`, `Resume.parse_status` — resume lineage/versioning
- `ResumeAnalysis` model + repository methods (`latest_analysis`, `add_analysis`, `list_lineage`)
- `DocumentRepository` (didn't exist before — needed for exports and cover letters)
- `StorageService` — `StorageBackend` interface + `LocalFileStorage` implementation, path-traversal-safe, S3 swap-in ready
- `ResumeParserService` — PDF (pypdf) / DOCX (python-docx) text extraction + Claude-based structuring (transcribe-only prompt)
- `ResumeAnalysisService` — ATS score, skill extraction, strengths/weaknesses, optional target-job missing-skills
- `fabrication_guard.py` — `check_for_fabrication()`, a real post-hoc check (not just a prompt instruction) used by both customization and cover letter generation
- `ResumeCustomizationService` — tailors resume content for a job, versioned as a new `Resume` row, verified against the fabrication guard before persisting
- `CoverLetterService` — personalized, company/role-specific, same fabrication guard
- `DocumentExportService` — resume/cover-letter → PDF (reportlab) and DOCX (python-docx)
- Celery tasks `parse_resume_task`, `analyze_resume_task` (available for future async use — see Deviations below)
- API: `POST /resumes/upload`, `GET /resumes/{id}`, `GET /resumes/{id}/versions`, `POST /resumes/{id}/analyze`, `GET /resumes/{id}/analysis`, `POST /resumes/{id}/customize`, `POST /resumes/{id}/export`, `POST /applications/{id}/cover-letter`, `GET /documents/{id}`
- Frontend: `/resumes` list page, `/resumes/[id]` detail page (ATS score gauge, extracted skills, strengths/weaknesses, export), `ResumeUploadDropzone`, `SkillTagList`, `ExportButtons` components, `lib/resumes.ts` hooks
- `require_owner()` shared ownership-check helper in `api/deps.py`
- `check_rate_limit()` — Redis-backed, fails open on Redis outage, wired into `/analyze`, `/customize`, `/cover-letter`
- Alembic migrations `0001_initial_schema` (captures Sprint 1's schema — none existed before) and `0002_resume_intelligence` (additive-only)
- New tests: `test_fabrication_guard.py`, `test_storage_service.py`, `test_resume_intelligence.py`

### Changed
- `ResumeCreate`/`ResumeRead` relocated from `api/v1/endpoints/resumes.py` to `domain/schemas/resume.py`, and `content` is now typed as `ResumeContent` (validated) instead of an untyped `dict` — a deliberate, documented tightening of `POST /resumes`'s input contract, not an accidental break
- `requirements.txt`: added `pypdf` (PDF text extraction; `reportlab` only writes PDFs, it doesn't read them)
- `docker-compose.yml`: added `resume_storage` named volume, mounted on `backend` and `celery_worker`
- `config.py`: added `STORAGE_ROOT`, `MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_RESUME_MIME_TYPES`, `AI_CALL_RATE_LIMIT_PER_HOUR` (additive)

### Deviations from the approved design
- **Synchronous endpoints instead of Celery + polling.** The design proposed `202 Accepted` + poll for upload/analyze. Implemented endpoints call the services directly and return the result, matching Sprint 1's existing convention (`POST /jobs/{id}/match` is synchronous). The Celery tasks were still built and are wired into the app, so switching any endpoint to async-with-polling later is a small change, not a rewrite.
- **Fabrication guard is a heuristic, not a semantic proof.** It flags capitalized tokens absent from the source resume text — good at catching invented companies/skills/technologies, not a substitute for human review of generated content. This is disclosed to the point of returning the specific flagged terms in the 422 response rather than a generic failure.

### Fixed
- N/A (additive sprint; nothing in Sprint 1 was broken — see Security/Performance review below)

---

## Sprint 2 — Self/Architecture/Security/Performance Review

**Self-review:** every service, repository, and endpoint listed above was written in full (no placeholders); `grep` for TODO/FIXME/NotImplementedError confirms no stubs were left in application code. All new Python files pass `py_compile`. Not independently verified: this sandbox has no network access, so `pytest` was not actually executed — review test logic by hand before trusting it in CI.

**Architecture review:** no Sprint 1 service, repository, or ATS adapter was modified — only `resumes.py`'s local schemas were relocated (per the approved design) and `Resume`/model `__init__.py` got additive columns. New code follows existing conventions: repository pattern, service layer, `CurrentUser`/`DbSession` deps, strict-JSON Claude contracts matching `MatchingService`'s established shape.

**Security review:** upload MIME/size validated before any bytes touch disk or Claude; `LocalFileStorage` rejects path traversal; ownership checks centralized via `require_owner` (404, not 403, to avoid existence leaks) and used by every new endpoint; AI-calling endpoints are now rate-limited (previously-dead config wired up); generated resume/cover-letter content is checked against the source before being persisted or returned.

**Performance review:** text extraction + AI structuring/analysis/customization are all synchronous within the request (see Deviations above) — acceptable at current scale matching Sprint 1's own `/jobs/{id}/match` pattern, but the first place to move to background execution if resume uploads become high-volume; the Celery tasks already exist for that migration. `DocumentExportService` is pure CPU-bound formatting (no I/O wait), safe to stay synchronous indefinitely.

---

## Sprint 1 — Core Platform + Job Discovery (complete)
- FastAPI backend: clean architecture, repository pattern, JWT auth
- Domain models: User, Company, Job, JobMatchScore, Application, Resume, Document, Notification, InterviewPrep
- ATS adapters: Greenhouse, Lever, Ashby, SmartRecruiters (public job-board APIs)
- JobDiscoveryService (idempotent sync), MatchingService (Claude-based scoring)
- Application pipeline with status history
- Next.js 14 dashboard: job search/filter, match-score signal ring
- Docker Compose, Alembic scaffolding, Celery beat, pytest suite
