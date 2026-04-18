#!/bin/bash
# One-command startup for Spectra (Gemini Live + Offline Ollama support)
# Usage: ./run-offline.sh [gemini|ollama]
# Default: gemini (Gemini Live API)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000
OLLAMA_URL="http://127.0.0.1:11434"

# Get provider from argument, default to gemini
PROVIDER="${1:-gemini}"

if [ "$PROVIDER" = "ollama" ]; then
    echo "Starting Spectra in Offline Mode (Ollama + Gemma 4)"
    echo "===================================================="
else
    echo "Starting Spectra in Gemini Live Mode (Primary)"
    echo "============================================="
fi

# Check if Ollama is running (only needed for offline mode)
if [ "$PROVIDER" = "ollama" ]; then
    echo ""
    echo "Checking Ollama..."
    if ! curl -s $OLLAMA_URL/api/tags > /dev/null 2>&1; then
        echo "ERROR: Ollama not running on $OLLAMA_URL"
        echo "Start Ollama first: ollama serve"
        exit 1
    fi
    echo "OK: Ollama running"
fi

# Kill any existing processes on our ports
echo ""
echo "Cleaning up existing processes..."
lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
sleep 1

# Start Backend
echo ""
echo "Starting Backend..."
cd "$REPO_ROOT/backend"

if [ "$PROVIDER" = "ollama" ]; then
    SPECTRA_PROVIDER=ollama python3 -m uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT > /tmp/spectra-backend.log 2>&1 &
else
    # Gemini mode - requires GOOGLE_API_KEY
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "Note: GOOGLE_API_KEY not set. Gemini Live mode needs API key."
        echo "Set it: export GOOGLE_API_KEY=your-api-key"
    fi
    python3 -m uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT > /tmp/spectra-backend.log 2>&1 &
fi

BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo "Logs: tail -f /tmp/spectra-backend.log"

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:$BACKEND_PORT/api/system-info > /dev/null 2>&1; then
        BACKEND_INFO=$(curl -s http://127.0.0.1:$BACKEND_PORT/api/system-info)
        BACKEND_MODE=$(echo $BACKEND_INFO | grep -o '"provider":"[^"]*' | cut -d'"' -f4)
        echo "OK: Backend ready (provider: $BACKEND_MODE)"
        break
    fi
    sleep 0.5
done

# Start Frontend
echo ""
echo "Starting Frontend..."
cd "$REPO_ROOT/frontend"
export NEXT_PUBLIC_WS_URL="ws://localhost:$BACKEND_PORT/ws"
npm run dev -- -p $FRONTEND_PORT > /tmp/spectra-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
echo "Logs: tail -f /tmp/spectra-frontend.log"

# Wait for frontend to be ready
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:$FRONTEND_PORT > /dev/null 2>&1; then
        echo "OK: Frontend ready"
        break
    fi
    sleep 0.5
done

echo ""
echo "=========================================="
if [ "$PROVIDER" = "ollama" ]; then
    echo "SPECTRA IS READY - OFFLINE MODE"
else
    echo "SPECTRA IS READY - GEMINI LIVE MODE"
fi
echo "=========================================="
echo ""
echo "Open: http://localhost:$FRONTEND_PORT"
echo ""
if [ "$PROVIDER" = "gemini" ]; then
    echo "Mode: Gemini Live (Primary)"
    echo "To switch to Offline: Click 'Offline' button in header"
else
    echo "Mode: Offline Ollama (Secondary)"
    echo "To switch to Gemini: Click 'Gemini Live' button in header"
fi
echo ""
echo "To stop: Press Ctrl+C"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "Done"
}

trap cleanup EXIT

# Keep running
wait
