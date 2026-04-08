#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== SpreadHunter — startup ==="

# ── Backend setup ──────────────────────────────────────────────────────────────
echo "[1/4] Setting up Python environment…"
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

# Copy .env if it doesn't exist
if [ ! -f "$ROOT/.env" ] && [ -f "$ROOT/.env.example" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "      Created .env from .env.example"
fi

# ── Frontend setup ─────────────────────────────────────────────────────────────
echo "[2/4] Installing frontend dependencies…"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  npm install --silent
fi

# ── Start backend ──────────────────────────────────────────────────────────────
echo "[3/4] Starting FastAPI backend on http://localhost:8000 …"
cd "$ROOT/backend"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Start frontend ─────────────────────────────────────────────────────────────
echo "[4/4] Starting React frontend on http://localhost:3000 …"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend  →  http://localhost:8000"
echo "  Frontend →  http://localhost:3000"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# Wait and clean up on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT INT TERM
wait
