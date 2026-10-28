# ExcelPoint

Study-only app (the career features were removed on 2026-10-28): users upload course materials (PDF, Word, audio/video), and **XP**, a chat assistant, answers **only from those materials** with citations (strict RAG). It also generates summaries, flashcards (SM-2 spaced repetition) and quizzes, and scores its own answer quality (AI Insights).

## Working with Lord Soma

- Call the user **Lord Soma**. Be direct, plain language, lead with the answer. No em dashes or en dashes in prose.
- **Commit after each fix or step, straight to `main`**, with 2-line messages (subject, blank line, one body line). **Push only when asked.**
- Never claim something works without a real check (tests, build, or running it), and show the output. Fix root causes; never weaken tests.
- **Never read, print or commit `.env`** (it lives at the repo root). Ask before anything destructive (deleting data, migrations that drop things, force push).
- When a decision is genuinely theirs (product or UX), ask one short question with options; otherwise pick the sensible default and say so.

## The new frontend (Option A): built, Oct 2026

The UI is a **React app in `frontend/`** (React 19, React Router 7, TanStack Query 5, Motion, Vite 8; plain CSS ported from the Figma prototype, no Tailwind), served by Django at **`/app/`**:

- `config/views.app_shell` serves the built `static/app/index.html` for every `/app/` route. Only `/app/login`, `/app/register` and `/app/welcome` are public; everything else redirects to `/app/login?next=…` (`LOGIN_URL`).
- Auth is Django **session cookies + CSRF**: the app reads the `csrftoken` cookie (set by `/api/me/` and the shell) and sends `X-CSRFToken`. Sign-in/register/logout are plain Django views (`users/auth_api.py`) so CSRF is checked for signed-out visitors too.
- Every old page that was rebuilt **redirects** into the app, keeping its URL name (`/`, subjects, review, quizzes, insights, notifications, settings, password, login, register). The removed career pages (`/learning/*`, `/users/profile/`, achievements, education, certifications) and the old `/users/logout/` page redirect to `/app/`.
- Every app endpoint is owner-scoped and tested. Shared styles load first in `frontend/src/main.tsx`; each page imports its own CSS from `frontend/src/styles/`.
- The old chat widget (`src/`, root `package.json`), the old templates for rebuilt pages and the old dashboard code were deleted on 2026-10-26. The career features (the `learning/` app, profile/education/certification/achievement pages and models, the career fields on `User`) and `base.html`, Bootstrap and `static/css/` went on 2026-10-28; `UserProfile` keeps only `education_level`; no Django templates are left (only the admin's).

### Design source (Figma Make)

- File: https://www.figma.com/make/BtWrFc23yiYRVO7DQHYyPT/ExcelPoint-Study-App-UI (fileKey `BtWrFc23yiYRVO7DQHYyPT`).
- It is a **Make** file, so `get_metadata`, `get_screenshot` and `create_session` do **not** work on it. Read it with `get_design_context(fileKey, nodeId="0:1")` (load the `figma:figma-design-to-code` skill first). That returns MCP resources: `src/App.tsx` (about 3,700 lines, every screen as a component), `src/index.css` (design tokens and all styles), 4 images. Treat it as a high-fidelity reference to adapt, not code to paste.
- The prototype uses React 19, Tailwind v4 and Vite 8, and switches screens with in-memory state (no router); the real app needs real routes.
- The design's "Course progress %" isn't used: subject cards show cards due and the latest quiz score.

### Agreed design decisions

- Colours: brand blue `#2563EB` (hover `#1D4ED8`); **AI gradient `#667EEA → #764BA2` only on XP/AI surfaces**; success mint (`#06A77F` light, `#06D6A0` dark); warning `#F59E0B`; error `#EF4444`; text `#1E293B`, muted `#64748B`, border `#E2E8F0`, background `#F8FAFC`. Full **light + dark** themes (tokens in the Make `index.css`).
- Clean and focused (Linear/Notion-like), Inter, 8px radius, subtle shadows. Collapsible **left sidebar**, which becomes a bottom tab bar on mobile.
- **XP is a full chat page** per subject, with conversation history on the left and a collapsible Sources panel on the right.
- Home is a **"Today" study queue** (due cards, suggestions, continue chatting, subjects).
- **ExcelPoint is study-only.** Career ideas (study plan, courses, achievements) are not coming back; study features such as streaks or an exam-date goal replace them.
- Desktop 1440 + mobile 390.

### Components and motion inspiration

For better components and **smooth animations**, study and adapt patterns from:
- https://bencho.dev/
- https://easyui.site/

Motion should feel calm and fast: respect `prefers-reduced-motion`, and never animate in a way that slows studying (no long blocking transitions).

## Architecture

| App | Role |
|---|---|
| `subjects/` | Core: subjects, materials, chunks (pgvector), chat (`services/rag_service.py`), quizzes, flashcards + SM-2 (`services/spaced_repetition.py`), suggestions (`services/recommendations.py`), Celery tasks (`tasks.py`) |
| `reasoning/` | Answer pipeline: rewrite (follow-ups only), retrieve, generate (streamable), verify, retry, confidence; traces (`ReasoningSession`), evaluations, judge, Insights + trace API (`app_api.py`) |
| `retrieval/` | Retrieval pipeline, embeddings, reranking, metrics, benchmark (`benchmark.py`) |
| `users/` | Custom User, Google OAuth, notifications (`Notification`), settings, change password |
| `config/` | Settings, URLs, Celery (`celery.py`, beat schedule in settings) |
| `frontend/` | The React app at `/app/` (its own package.json, tests and build to `static/app/`) |

**Chat flow:** search similarity gate (≥0.3; nothing relevant means a fixed "not in your materials" reply with **no LLM call**) → small talk uses one call → otherwise the reasoning pipeline (2 LLM calls; 3 for follow-ups). The answer streams over SSE from `POST /api/subjects/<id>/chat/stream/` (`token` / `done` / `error` events; `done` carries the saved message, which is authoritative). There is a per-user LLM rate limit (`LLM_RATE_LIMIT`, default 60/hour).

### API used by the app

- Shell and account: `GET/PATCH /api/me/`, `POST /api/me/password/`, `GET /api/notifications/`, `POST /api/notifications/read/`, `POST /api/auth/{login,register,logout}/` (Google stays `/users/google/login/`).
- Home: `GET /api/home/`. Subjects: `/api/subjects/` (+ `summary`, `materials`, `flashcards`, `quizzes`, `upload_material`), `DELETE /api/materials/<id>/`.
- Chat: `/api/subjects/<id>/chat/{session,sessions,messages,stream}/`; `messages` (GET and POST) and `stream` take an optional `session_id` to open or continue a past conversation.
- Review: `GET /api/review/queue/?subject=`, `POST /api/review/grade/`.
- Quizzes: `POST /api/quiz/<id>/attempts/ {fresh}`, `GET /api/quiz/attempts/` (history), `GET /api/quiz/attempts/<id>/` (status + questions without answers), `POST …/submit/`, `GET …/results/` (`subjects/quiz_api.py`). A failed fresh-question job stores `dynamic_questions = []`.
- Insights: `GET /api/reasoning/insights/?days=7|30|90`, `GET /api/reasoning/sessions/<uuid>/trace/`.

## Deployment

`Dockerfile` (builds the app, bakes in the embedding model, `collectstatic`), `docker-compose.yml` (db, redis, migrate, web, worker, beat, caddy), `Caddyfile` (HTTPS), `gunicorn.conf.py` (threaded workers, model preload). whitenoise serves `/static/`; `/media/` is never served when `DEBUG` is off. Production-only settings come from env: `CACHE_URL` (shared Redis cache for rate limits), `REDIS_URL` (Celery), `NUM_PROXIES` (trusted proxies for the client IP and HTTPS; keep 0 without a proxy), `SECURE_HSTS_SECONDS`.

## Commands

CI (`.github/workflows/ci.yml`) runs the backend checks and tests on Postgres 15 + pgvector and Redis, and the app's typecheck, tests and build, on every push to `main` and every PR.

```bash
TESTING=1 venv/bin/python manage.py test   # backend (~250 tests); test runs blank OPENAI_API_KEY, so nothing spends tokens
npm --prefix frontend test                 # the app's tests (vitest); also: cd frontend && npx tsc --noEmit
npm --prefix frontend run build            # rebuild the app into static/app/ (Django serves it at /app/)
npm --prefix frontend run dev              # Vite on :5173, proxies /api etc. to runserver on :8000
venv/bin/python manage.py runserver        # plus: redis-server, celery worker, celery beat
venv/bin/python -m celery -A config.celery.app worker -l INFO --pool=solo   # the venv's celery shebang is broken
venv/bin/python -m celery -A config.celery.app beat -l INFO   # daily flashcard reminders
venv/bin/python manage.py benchmark_retrieval docs/retrieval_benchmark.example.json
venv/bin/python manage.py judge_answers    # optional LLM judge backlog
```

## Environment gotchas

- Postgres 15 (Homebrew) on **port 5433**, with **pgvector 0.8.0 built from source**: Homebrew's pgvector only supports PG 17/18. A `brew upgrade` can wipe it; rebuild with `make PG_CONFIG=/opt/homebrew/opt/postgresql@15/bin/pg_config && make install`.
- The venv's `pip` shebang is broken: use `venv/bin/python -m pip`.
- Node 25: `frontend/src/test/setup.ts` swaps in jsdom's `localStorage` (Node's built-in one shadows it).
- The app's test helper `mockApi` treats a plain object as a 200 body; use `reply(status, body)` for other statuses.
- Disk space on this Mac runs low; a crash-looping Homebrew Postgres 14 once filled it with a 1 GB log (now stopped).
- In zsh, quote `grep --include="*.py"` patterns, and don't expect `$VAR` to word-split.
- Default model `gpt-5.4-mini` (`OPENAI_MODEL`). All OpenAI calls use **`max_completion_tokens`**, not `max_tokens`, which newer models reject.
- `DEBUG` defaults to off; the local `.env` sets `DEBUG=True`.

## Done so far (Oct 2026)

- Fixed the original bugs: quiz FK, Whisper import, OAuth (state check, open redirect, verified email), IDOR in the APIs, S3 handling, secrets moved to env, test discovery.
- Completed all 5 stages of `docs/stages.md`: retrieval (pgvector + HNSW, benchmark); reasoning pipeline; evaluation (heuristic + optional judge, quality API); observability (AI Insights pages, traces, JSON logs); workflows (upload chord → flashcards, quiz and summary + notification, SM-2 review, reminders, suggestions).
- Streaming answers, LLM rate limit, consistent verifier, confidence fixes, background dynamic quizzes, change-password fix, ~1,300 lines of dead code removed, frontend tests repaired (108 then; the new app has 59).

## Backlog

- First real deploy (README "Deploying"): `docker-compose.yml` + `Dockerfile` + `Caddyfile` are written and CI builds the image, but nothing has run on a server yet.
- Email verification (unverified emails can block a Google sign-up, though no longer take over an account).
- Tune the 0.3 similarity threshold with real questions (`benchmark_retrieval`).
- Hybrid keyword + vector search.
- Remove the legacy `QuizQuestion` / `QuizAttempt` models (needs a migration).
- Audio/video uploads need Whisper; `pydub` may break on Python 3.13.
