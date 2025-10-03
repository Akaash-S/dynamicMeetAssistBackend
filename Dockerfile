FROM python:3.11-slim AS base

# Prevents Python from writing pyc files and enables unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (build, postgres, and libsndfile/ffmpeg-like tools if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    ca-certificates \
    libpq5 \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies separately for better caching
# Copy requirements from the same directory as this Dockerfile (backend/)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source (everything in backend/)
COPY . /app

# Expose default Gunicorn port (Render sets PORT env; we will bind to it)
EXPOSE 8000

# Healthcheck (expects /api/health)
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD \
  curl -fsS http://localhost:8000/api/health || exit 1

# Gunicorn config (threads to avoid blocking, adjust workers per CPU)
ENV WEB_CONCURRENCY=2 \
    GUNICORN_TIMEOUT=120 \
    PORT=8000 \
    PYTHONPATH=/app

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Start via entrypoint; binds to PORT and validates import before boot
WORKDIR /app
CMD ["/app/entrypoint.sh"]


