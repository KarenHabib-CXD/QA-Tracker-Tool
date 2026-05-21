#!/usr/bin/env bash
# QA Sprint Tracker — starts backend + frontend together
# Usage: bash run.sh
# Stop:  Ctrl+C  (kills both)

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
UVICORN="$ROOT/.venv/bin/uvicorn"
STREAMLIT="$ROOT/.venv/bin/streamlit"

echo ""
echo "🧪 QA Sprint Tracker"
echo "──────────────────────────────────"
echo "  Backend  → http://127.0.0.1:8000"
echo "  Frontend → http://localhost:8501"
echo "  Stop     → Ctrl+C"
echo "──────────────────────────────────"
echo ""

# Start backend in background
cd "$ROOT"
"$UVICORN" backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Give backend a second to start
sleep 1

# Start frontend in foreground (Ctrl+C will kill it)
"$STREAMLIT" run frontend/app.py --server.port 8501 --server.headless true

# When frontend is stopped, also kill backend
kill $BACKEND_PID 2>/dev/null
echo ""
echo "✅ QA Sprint Tracker stopped."
