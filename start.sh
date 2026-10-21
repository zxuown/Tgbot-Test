#!/bin/sh
set -e

echo "=================================================="
echo "  Focus Bot — Production Container Starting"
echo "  Environment: ${APP_ENV:-production}"
echo "  Bot Mode:    ${BOT_MODE:-polling}"
echo "  Port:        ${PORT:-8000}"
echo "=================================================="

# Run migrations if enabled (default true)
if [ "${AUTO_MIGRATE:-true}" != "false" ]; then
    echo "[1/2] Applying database migrations (alembic upgrade head)..."
    alembic upgrade head || {
        echo "Migration failed! Exiting."
        exit 1
    }
    echo "Migrations applied successfully."
else
    echo "[1/2] Skipping auto-migrations (AUTO_MIGRATE=false)."
fi

echo "[2/2] Launching application..."
case "${BOT_MODE:-polling}" in
    "api")
        exec uvicorn app.api.app:app --host "${API_HOST:-0.0.0.0}" --port "${PORT:-8000}"
        ;;
    *)
        exec python -m app.main
        ;;
esac
