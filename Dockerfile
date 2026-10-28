# Stage 1: build the React app into /src/static/app
FROM node:25-slim AS app
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Django app (web, Celery worker and beat all run this image)
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/opt/huggingface
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .
# The CPU build of torch first: the default Linux wheel pulls several GB of CUDA libraries
RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt
# Bake the embedding model in, so the first question after a deploy doesn't download it
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .
COPY --from=app /src/static/app static/app
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p media && chown app media
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi"]
