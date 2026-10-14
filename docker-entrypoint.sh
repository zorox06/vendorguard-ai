#!/bin/sh
set -e

# If arguments are passed to container, run them directly (e.g. docker run ... bash)
if [ "$#" -gt 0 ] && [ "$1" != "start" ]; then
  exec "$@"
fi

echo "=========================================================="
echo " Starting VendorGuard AI Unified Production Stack"
echo " Single Container: UI (Next.js), API (FastAPI), Worker"
echo "=========================================================="

export PYTHONPATH="/app"
export DATABASE_URL="${DATABASE_URL:-sqlite:////app/vendorguard.db}"
export ASYNC_DATABASE_URL="${ASYNC_DATABASE_URL:-sqlite+aiosqlite:////app/vendorguard.db}"
export BACKEND_INTERNAL_URL="${BACKEND_INTERNAL_URL:-http://127.0.0.1:8000}"
export PORT="${PORT:-3000}"

# 1. Initialize clean database schema
echo "[1/4] Ensuring database schema is initialized..."
python3 -c "from backend.app.adapters.storage import init_db; init_db(); print('Database tables verified.')"
if [ "${SEED_DEMO_DATA}" = "true" ]; then
  echo "SEED_DEMO_DATA is enabled. Seeding demo dataset..."
  python3 -m backend.app.adapters.seed_db || echo "Seeding script completed."
fi

# 2. Start FastAPI Backend in background on 127.0.0.1:8000
echo "[2/4] Starting FastAPI backend on http://127.0.0.1:8000..."
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend health check
echo "Waiting for backend to become healthy..."
MAX_RETRIES=30
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "FastAPI backend is healthy (pid $BACKEND_PID)!"
    break
  fi
  sleep 1
  COUNT=$((COUNT + 1))
done

# 3. Start durable background worker
echo "[3/4] Starting durable background monitoring worker..."
python3 -m backend.worker &
WORKER_PID=$!

# Trap signals for graceful shutdown
cleanup() {
  echo "Received shutdown signal. Stopping services..."
  kill -TERM "$WEB_PID" 2>/dev/null || true
  kill -TERM "$WORKER_PID" 2>/dev/null || true
  kill -TERM "$BACKEND_PID" 2>/dev/null || true
  wait "$WEB_PID" 2>/dev/null || true
  wait "$WORKER_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  echo "All services stopped."
  exit 0
}

trap cleanup INT TERM

# 4. Start Next.js Frontend Server on 0.0.0.0:3000
echo "[4/4] Starting Next.js UI on http://0.0.0.0:${PORT}..."
cd /app/apps/web
./node_modules/.bin/next start -p "$PORT" -H 0.0.0.0 &
WEB_PID=$!

echo "=========================================================="
echo " VendorGuard AI is ready!"
echo " Web UI and UX: http://localhost:${PORT}"
echo " API Backend:   Proxied internally to :8000"
echo "=========================================================="

# Wait for the frontend server process
wait "$WEB_PID"
