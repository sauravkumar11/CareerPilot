# Deployment Guide

**Honesty check first:** nothing below has been deployed or tested against a real Vercel/Render
account — those platforms aren't reachable from the sandbox this was written in, and no account
was available to verify with. `render.yaml` is a best-effort blueprint based on Render's documented
schema; treat it as a strong starting point, not a guarantee. The CI workflow (`.github/workflows/ci.yml`),
by contrast, *was* fully verified — every script inside it was actually run locally before committing.

## Frontend — Vercel

Next.js on Vercel is close to zero-config. No config file needed.

1. [vercel.com/new](https://vercel.com/new) → **Import Git Repository** → select `CareerPilot`.
2. Vercel will try to build from the repo root, which is wrong (the Next.js app is in `frontend/`).
   In the import screen, expand **Root Directory** and set it to `frontend`.
3. Framework preset should auto-detect as **Next.js** — leave build/output settings as default.
4. Add an environment variable: `NEXT_PUBLIC_API_URL` = the backend's public URL once it exists
   (e.g. `https://careerpilot-backend.onrender.com/api/v1`). You can add this now with a placeholder
   and update it after the backend is deployed — Vercel redeploys automatically when you change env
   vars.
5. Deploy. Vercel's build runs in a normal internet-connected environment, so the Google Fonts
   fetch that failed in the development sandbox (see `PROJECT_STATUS.md`) should succeed here —
   but this specific claim is unverified; watch the build log on first deploy.

## Backend — Render

### Option A: Blueprint (`render.yaml`) — faster, less certain to work first try

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** → connect the
   `CareerPilot` repo. Render reads `render.yaml` from the repo root automatically.
2. Render will show you a preview of every service it's about to create (1 Postgres, 1 Redis, 1 web
   service, 2 workers) before creating anything — review it. If any field is rejected (most likely
   candidate: the `type: keyvalue` Redis service, since Render's exact naming for this has changed
   over time), Render's error message will tell you which key, and you can fix it directly in the
   dashboard's blueprint editor rather than starting over.
3. Set the two `sync: false` secrets manually in the dashboard once services exist:
   `ANTHROPIC_API_KEY` (all three services) and `BACKEND_CORS_ORIGINS` (web service — set to your
   Vercel URL, e.g. `https://careerpilot.vercel.app`).
4. The `celery-worker` and `celery-beat` services need the *same* `SECRET_KEY` the web service
   generated (JWTs are signed with it) — copy the value Render generated for the web service's
   `SECRET_KEY` into both worker services' env vars manually.

### Option B: Manual setup — slower, more reliable

If the blueprint import fails or you'd rather see each piece, create these one at a time in the
Render dashboard, all pointed at the same GitHub repo:

1. **PostgreSQL** (New → PostgreSQL) — note the internal connection string it gives you.
2. **Redis / Key Value** (New → Redis, or whatever Render currently calls it) — note its connection
   string too.
3. **Web Service** (New → Web Service) — Docker runtime, Dockerfile path `backend/Dockerfile`,
   Docker context `backend`. Health check path `/health`. Env vars: everything in
   `backend/.env.example`, with `DATABASE_URL`/`REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`
   pointed at the connection strings from steps 1–2, plus a real `SECRET_KEY` (generate one:
   `openssl rand -hex 32`) and your real `ANTHROPIC_API_KEY`.
4. **Worker** (New → Background Worker) — same Docker settings as the web service, but override the
   start command to `celery -A app.core.celery_app worker --loglevel=info`. Same env vars, same
   `SECRET_KEY` as the web service.
5. **Beat** (New → Background Worker again) — same as step 4, but the start command is
   `celery -A app.core.celery_app beat --loglevel=info`.
6. After the web service deploys, run the migration once (Render's dashboard has a "Shell" tab per
   service): `python -m alembic upgrade head`.

### Either way, after the backend is live

- Go back to Vercel and set `NEXT_PUBLIC_API_URL` to the real backend URL + `/api/v1`.
- Set `BACKEND_CORS_ORIGINS` on the backend to the real Vercel URL, or the browser will block every
  request with a CORS error.
- Seed the initial companies: use the backend's Shell tab to run
  `python -m scripts.seed_companies`.

## What to check once it's actually live

- `GET https://<backend-url>/health` → `{"status": "ok", ...}`
- Register/login through the deployed frontend
- Trigger a company sync — this is the first time the app will reach the *real* Greenhouse/Lever
  APIs (blocked in the dev sandbox, but should work fine from Render's normal network)
- Set a real `ANTHROPIC_API_KEY` and try a resume upload — this is the first time AI generation
  will run for real end-to-end (also blocked/placeholder-only in the dev sandbox)

These are exactly the things this project's own verification pass (see `PROJECT_STATUS.md`)
couldn't test — a live deployment is genuinely the first opportunity to.
