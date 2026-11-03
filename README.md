# ExcelPoint

![ExcelPoint: learn faster from your own notes](branding/link-preview-1200x630.png)

ExcelPoint is a study app. Students upload their own class material (PDF or Word notes, or lecture recordings), and every file becomes a summary, flashcards and a quiz. **XP**, the AI study assistant, answers questions using only those files, shows the exact passage behind each answer, and says "Not in your materials" when a question isn't covered.

Free while in beta. [Product brief](https://claude.ai/artifact/76HBvLPusaVo8TZEcE9FTm) · [Demo video](https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view)

## What a student can do

- **Subjects:** one per class (for example Biology), holding that class's files, flashcards, quizzes and chats.
- **Uploads:** PDF, Word (.docx), audio (MP3, WAV, M4A) and video (MP4, MOV, AVI), up to 100 MB; recordings up to 3 hours. Broken or unsupported files are refused with a reason, and a notification arrives when processing finishes or fails.
- **XP chat:** answers only from that subject's files, streams the answer, shows its sources, and marks whether every statement was checked against them. "How was this answered?" explains the answer in plain words.
- **Flashcards:** spaced repetition (SM-2, the method Anki uses). On a new card, Hard comes back in 1 day, Good in 3 and Easy in 7.
- **Quizzes:** one per file, fresh questions on request, explained results, and "Save & exit" to resume later.
- **Today page:** cards to review, ranked next steps and recent conversations.
- **Insights:** answer quality over time, and a full trace for each answer.
- **Account:** email and password (with an emailed reset link) or Google sign-in, light and dark themes, download all your data as a zip, delete any file, subject, chat or the whole account.

Works on phones (tested at 375 px on slow 3G). Privacy and Terms pages are at `/app/privacy` and `/app/terms`.

## How XP answers

XP answers **only from the student's uploaded files**:

1. The question is embedded (`all-MiniLM-L6-v2`, on our own server) and matched against that subject's passages in Postgres (pgvector, HNSW index).
2. If nothing scores above the similarity cut-off (0.3), XP replies "Not in your materials" and no AI is called. Broad requests such as "Summarise the key ideas" use the closest passages instead.
3. Otherwise the reasoning pipeline runs: retrieve, generate a strict cited answer, verify each statement, and retry if unfaithful. Follow-ups are first rewritten from the chat history. That is 2 AI calls for a normal question and 3 for a follow-up.
4. Every answer is saved as a trace and scored (faithfulness, unsupported statements, retrieval similarity), and logged as one JSON line (`"event": "chat_answer"`).

After an upload, a Celery worker reads the file (python-docx for Word, pypdf for PDF) or has it transcribed by OpenAI `gpt-transcribe` (ffmpeg first cuts recordings into chunks under the API's 25 MB limit). It then splits and indexes the text and writes flashcards, a quiz and a summary in parallel.

| Tool | Where |
| --- | --- |
| Quality dashboard | `/app/insights` |
| Per-answer trace | `/app/insights/<session-id>`, or "How was this answered?" in the chat |
| Retrieval benchmark (hit@k, MRR) | `python manage.py benchmark_retrieval docs/retrieval_benchmark.example.json` |
| Optional LLM judge (one extra call per answer) | `EVAL_LLM_JUDGE=True`, or `python manage.py judge_answers` |

## Tech stack

- **Backend:** Django 5.2 and Django REST Framework on Python 3.13; Celery and Redis for background work and the daily review reminder.
- **Database:** PostgreSQL with pgvector (HNSW index).
- **AI:** OpenAI chat models (default `gpt-5.4-mini`, set with `OPENAI_MODEL`) and `gpt-transcribe` for recordings; sentence-transformers embeddings run locally.
- **Frontend:** a React 19 and TypeScript app in `frontend/` (React Router, TanStack Query, Motion, Vite), served by Django at `/app/`. Answers stream over Server-Sent Events.
- **Brand:** the 3D "E" icon and the "Excel**P**oint" wordmark for the product, the purple 3D "XP" icon for the assistant. Originals are in `branding/`.

## Getting started

### Prerequisites

- Python 3.13+, Node.js 20+
- PostgreSQL 13+ with the [pgvector](https://github.com/pgvector/pgvector) extension (0.8+)
- Redis 6+
- ffmpeg (for audio and video uploads)

### Install

```bash
git clone https://github.com/Nwachukwu1300/excelpoint.git
cd excelpoint
python -m venv venv && source venv/bin/activate
python -m pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build        # builds the app into static/app/
cp .env.example .env                   # then fill in the database and OpenAI settings
python manage.py migrate
```

pgvector: on Postgres 17/18 with Homebrew, `brew install pgvector`; for other versions, build v0.8.0 against your server's `pg_config` (`make PG_CONFIG=... && make install`).

### Run

```bash
python manage.py runserver                                       # the app at http://localhost:8000/app/
python -m celery -A config.celery.app worker -l INFO --pool=solo # processes uploads, sends emails
python -m celery -A config.celery.app beat -l INFO               # daily flashcard reminders
redis-server
```

Without `EMAIL_HOST` in `.env`, password-reset emails are printed to the worker's console.

### Test

```bash
TESTING=1 python manage.py test          # backend; needs Postgres with pgvector and ffmpeg; never calls OpenAI
npm --prefix frontend test               # the app (Vitest); also: cd frontend && npx tsc --noEmit
```

CI runs both on every push to `main`, and builds the Docker image for amd64 and arm64.

## Deploying

One server with Docker runs everything: gunicorn, a Celery worker and beat, Postgres with pgvector, Redis, Caddy for HTTPS, and a nightly database backup.

**Free setup, step by step:** [docs/deploy-oracle.md](docs/deploy-oracle.md) (Oracle Cloud Always Free, a DuckDNS address and Gmail for password emails), with a one-command installer, `deploy/setup-server.sh`.

Any other server:

1. Point your domain's DNS at the server and open ports 80 and 443.
2. `cp .env.example .env`, then set `DOMAIN`, `ALLOWED_HOSTS` (your domain), `DEBUG=False`, a fresh `DJANGO_SECRET_KEY`, `DB_USER` and `DB_PASSWORD`, `OPENAI_API_KEY`, the `EMAIL_*` settings, and Google OAuth if you use it (`GOOGLE_OAUTH_REDIRECT_URI=https://<domain>/users/google/callback/`).
3. `docker compose up -d --build`. Migrations run first; Caddy fetches the certificate.
4. Once the site works over HTTPS, set `SECURE_HSTS_SECONDS=31536000` and run `docker compose up -d` again.

Uploads live in the `media` volume and the database in `pgdata`. The `backup` service keeps the last 7 nightly database dumps in the `backups` volume; copy them and `media` off the server too.

## Known limitations

- Scanned PDFs (pictures of text) can't be read yet.
- Email addresses are not verified yet.
- There is no daily upload limit per student yet; each upload costs a few AI calls.
- Without `CACHE_URL` (local runs), rate limits are counted per server process; docker compose sets a shared Redis cache.

## Contact

<mnfinance664@gmail.com>

---

Built by Mmesoma
