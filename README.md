# ExcelPoint - Learning Enhancement Platform

## 🎥 [Watch Demo Video](https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view)

## Project Overview
ExcelPoint is a learning enhancement platform designed to elevate the educational experience for everyone. My platform combines advanced content processing, interactive learning tools, and personalized study assistance to transform how people learn and retain knowledge.

## Mission
To bridge the gap between traditional learning methods and modern educational needs by providing intelligent, adaptive learning experiences that cater to diverse learning styles and professional requirements.

## Features

### Study from your own materials
- **Uploads:** PDF and Word documents; audio and video too when Whisper is installed (transcribed, then treated like text).
- **Processing in the background:** files are chunked and embedded with Celery, then flashcards, a quiz and a summary are generated in parallel. A notification tells you when they're ready.
- **XP, the chat assistant:** answers only from your uploaded materials, cites the file it used, and says plainly when your notes don't cover a question. Answers stream in as they're written.
- **Quizzes:** generated from your materials, including fresh questions on each retake, with scores and history.
- **Flashcards with spaced repetition:** SM-2 scheduling (the method Anki uses), a review page, and a daily reminder when cards are due.
- **Suggestions:** the Today page ranks next steps from your quiz scores, due cards, questions your notes couldn't answer, and untried quizzes.

### Quality and transparency
- **Verified answers:** a second model call checks each claim against your materials; unverified answers are marked.
- **AI Insights:** a dashboard of answer quality over time, and a per-answer trace showing the chunks, prompt, claims and timings.
- **Evaluation tools:** an optional LLM judge for answer relevance, and a retrieval benchmark (hit@k, MRR) on your own question set.

### Accounts and safety
- Email/password and Google sign-in (with state checks; Google accounts are matched by Google ID, never by email).
- Every query is limited to your own subjects; per-user rate limit on questions that call the LLM.
- Local or S3 file storage.

## Tech stack

- **Backend:** Django 5.2 and Django REST Framework on Python 3.13, Celery + Redis for background work and scheduled jobs.
- **Database:** PostgreSQL with pgvector (HNSW index) for semantic search.
- **AI:** OpenAI chat models (default `gpt-5.4-mini`, set with `OPENAI_MODEL`), `all-MiniLM-L6-v2` sentence-transformers embeddings, LangChain/Unstructured document loaders.
- **Frontend:** a React 19 + TypeScript app in `frontend/` (React Router, TanStack Query, Motion, Vite), served by Django at `/app/`; answers stream over Server-Sent Events.

## Running the tests

```bash
TESTING=1 python manage.py test   # backend (needs Postgres with pgvector; never calls OpenAI)
npm --prefix frontend test        # the React app (Vitest)
```

## Known limitations

- Without `CACHE_URL` (local runs), rate limits are counted per server process; docker compose sets a shared Redis cache.
- Emails are not verified yet.
- Audio/video uploads need Whisper installed and may hit `pydub` issues on Python 3.13.

## How XP answers (RAG pipeline)

XP answers **only from your uploaded materials**:

1. Your question is embedded (all-MiniLM-L6-v2) and matched against your chunks in Postgres (pgvector, HNSW index).
2. If nothing scores above the similarity threshold, XP says it isn't in your materials and no LLM is called.
3. Otherwise the reasoning pipeline runs: retrieve → generate (strict, cited) → verify claims → retry if unfaithful. Follow-ups ("give an example of that") are first rewritten using the chat history. That's 2 LLM calls for a normal question, 3 for a follow-up.
4. Every answer is saved as a trace and scored (faithfulness, unsupported-claim rate, retrieval similarity).

### Evaluation and debugging

| What | Where |
|---|---|
| Quality dashboard (trends, failures, retrieval stats) | `/insights/` |
| Per-answer trace (chunks, prompts, claims, stage timings) | `/insights/<session-id>/`, or "How was this answered?" in the chat |
| Quality data as JSON | `GET /api/reasoning/quality/?days=30` |
| Retrieval benchmark (hit@k, MRR) | `python manage.py benchmark_retrieval docs/retrieval_benchmark.example.json` |
| LLM-judge scoring (optional, costs one call per answer) | set `EVAL_LLM_JUDGE=True`, or run `python manage.py judge_answers` |

### Study workflows

After an upload is processed, a Celery chord generates flashcards, a quiz and a summary in parallel, then sends a notification (bell icon). Flashcards are scheduled with SM-2 spaced repetition (`/app/review`), a daily beat job reminds you when cards are due, and the Today page suggests next steps from your quiz scores, due cards and questions your notes couldn't answer.

Each answer also logs one JSON line (`"event": "chat_answer"`) with its path, chunk count, verification and per-stage timings.

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js 18+
- PostgreSQL 13+ with the [pgvector](https://github.com/pgvector/pgvector) extension (0.8+)
- Redis 6+

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd excelpoint
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up frontend**
   ```bash
   npm --prefix frontend install
   npm --prefix frontend run build   # builds into static/app/
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

5. **Install pgvector, then run migrations**
   ```bash
   # Postgres 17/18 via Homebrew: brew install pgvector
   # Other versions: build it against your server's pg_config
   git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
   cd pgvector && make PG_CONFIG=$(which pg_config) && make install PG_CONFIG=$(which pg_config)

   python manage.py migrate   # enables the extension and converts embeddings
   ```

6. **Start services**
   ```bash
   # Terminal 1: Django server
   python manage.py runserver
   
   # Terminal 2: Celery worker
   celery -A config.celery.app worker --loglevel=INFO
   
   # Terminal 3: Redis
   redis-server

   # Terminal 4: Celery beat (daily flashcard review reminders)
   celery -A config.celery.app beat --loglevel=INFO
   ```

## Deploying

One server with Docker runs everything: gunicorn, a Celery worker and beat, Postgres with pgvector, Redis, and Caddy for HTTPS.

1. Point your domain's DNS at the server and open ports 80 and 443.
2. `cp .env.example .env`, then set `DOMAIN`, `ALLOWED_HOSTS` (your domain), `DEBUG=False`, a fresh `DJANGO_SECRET_KEY`, `DB_USER`/`DB_PASSWORD`, `OPENAI_API_KEY`, and Google OAuth if you use it (`GOOGLE_OAUTH_REDIRECT_URI=https://<domain>/users/google/callback/`).
3. `docker compose up -d --build`. Migrations run first; Caddy fetches the certificate.
4. Once the site works over HTTPS, set `SECURE_HSTS_SECONDS=31536000` and run `docker compose up -d` again.

Uploads live in the `media` volume and the database in `pgdata`; back both up. The image bakes in the embedding model, and each gunicorn worker loads it at start, so the first question isn't slow.

## Demo & Screenshots

🎥 **[Watch the full demo video](https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view)** to see ExcelPoint in action!

## Contributing

I'm welcoming contributors



## Support
 Contact the mnfinance@gmail.com

---

**Built with ❤️ by Mmesoma**

