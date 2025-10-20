#!/usr/bin/env sh
set -e

echo "[entrypoint] Starting AI Meeting Assistant Backend..."
echo "[entrypoint] Python: $(python --version)"
echo "[entrypoint] Environment: ${FLASK_ENV:-production}"

# Validate required environment variables
echo "[entrypoint] Validating environment variables..."
if [ -z "${SECRET_KEY}" ]; then
  echo "[entrypoint][error] SECRET_KEY is required but not set"
  exit 1
fi

# Check database connection
echo "[entrypoint] Checking database connection..."
python -c "
import os
import sys
try:
    from config.database import init_db
    init_db()
    print('[entrypoint] Database connection successful')
except Exception as e:
    print(f'[entrypoint][error] Database connection failed: {e}')
    sys.exit(1)
"

# Verify Flask app importability
echo "[entrypoint] Verifying Flask app..."
python - <<'PY'
import sys
import os
try:
    import app
    print('[entrypoint] Flask app imported successfully')
    if not hasattr(app, 'app'):
        print('[entrypoint][error] Flask app variable not found')
        sys.exit(1)
    print('[entrypoint] Flask app variable found')
except Exception as e:
    import traceback
    print(f'[entrypoint][error] Failed to import Flask app: {e}')
    traceback.print_exc()
    sys.exit(1)
PY

# Set production-ready Gunicorn configuration
WORKERS=${WEB_CONCURRENCY:-2}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
PORT=${PORT:-8000}

echo "[entrypoint] Starting Gunicorn with ${WORKERS} workers on port ${PORT}"

# Launch Gunicorn with production settings
exec gunicorn \
  --workers ${WORKERS} \
  --worker-class gthread \
  --threads 4 \
  --timeout ${TIMEOUT} \
  --bind 0.0.0.0:${PORT} \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  --preload \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  app:app


