# ─────────────────────────────────────────────
#  ET-AI Content Engine — Dockerfile
#  Works on Linux, Mac, Windows, and any cloud
# ─────────────────────────────────────────────

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Copy project
COPY . .

# Don't copy secrets
# Make sure .dockerignore excludes .env and jobs.db

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
