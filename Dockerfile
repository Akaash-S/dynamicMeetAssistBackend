FROM python:3.11-slim AS base

# Prevents Python from writing pyc files and enables unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (build, postgres, and libsndfile/ffmpeg-like tools if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies separately for better caching
# Copy requirements from the same directory as this Dockerfile (backend/)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source (everything in backend/)
COPY . /app

# Expose Gunicorn port
EXPOSE 8000

# Healthcheck (expects /api/health)
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD \
  curl -fsS http://localhost:8000/api/health || exit 1

# Gunicorn config (threads to avoid blocking, adjust workers per CPU)
ENV WEB_CONCURRENCY=2 \
    GUNICORN_TIMEOUT=120

# Start via Gunicorn; the Flask app is defined as `app` in /app/app.py
WORKDIR /app
CMD ["bash", "-lc", "gunicorn -w ${WEB_CONCURRENCY} -k gthread --threads 4 --timeout ${GUNICORN_TIMEOUT} -b 0.0.0.0:8000 app:app"]


