# Multi-stage build for optimized production image
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Set build environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM python:3.11-slim

# Set production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    WEB_CONCURRENCY=4 \
    GUNICORN_TIMEOUT=120 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R app:app /app

# Copy application code
COPY --chown=app:app . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check with better configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Add labels for better container management
LABEL maintainer="AI Meeting Assistant Team" \
      version="1.0" \
      description="AI Meeting Assistant Backend API" \
      org.opencontainers.image.source="https://github.com/yourusername/ai-meeting-assistant"

# Start application
CMD ["./entrypoint.sh"]


