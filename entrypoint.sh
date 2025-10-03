#!/usr/bin/env sh
set -e

echo "[entrypoint] Starting container..."
echo "[entrypoint] Python: $(python --version)"

echo "[entrypoint] Validating required environment variables"
if [ -z "${SECRET_KEY}" ]; then
  echo "[entrypoint][warn] SECRET_KEY is not set. Set it in your service env vars."
fi

echo "[entrypoint] Verifying Flask app importability (module: app, object: app)"
python - <<'PY'
import sys
try:
    import app
    print('[entrypoint] Imported module app OK')
    if not hasattr(app, 'app'):
        print('[entrypoint][error] app module does not define a variable named \"app\"')
        sys.exit(3)
    else:
        print('[entrypoint] Found Flask app variable: app')
except Exception as e:
    import traceback
    print('[entrypoint][error] Failed to import app module:', e)
    traceback.print_exc()
    sys.exit(3)
PY

echo "[entrypoint] Launching Gunicorn"
exec gunicorn \
  -w "${WEB_CONCURRENCY:-1}" \
  -k gthread --threads 4 \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  -b 0.0.0.0:"${PORT:-8000}" \
  app:app \
  --log-level debug \
  --access-logfile - \
  --error-logfile -


