#!/bin/bash

# Start Spectra Backend
# Run this from anywhere - it will navigate to the correct directory

set -e

echo "🐍 Starting Spectra Backend..."
echo ""

# Navigate to the backend directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 Working directory: $SCRIPT_DIR"

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ] || [ ! -d "app" ]; then
    echo "❌ Error: Backend files not found in $SCRIPT_DIR"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and add your API key:"
    echo "   cp .env.example .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Find a free port starting from 8080
find_free_port() {
  for port in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089; do
    if ! lsof -ti:$port &>/dev/null; then
      echo $port
      return
    fi
  done
  echo "❌ No free port found in range 8080-8089" >&2
  exit 1
}

PORT=$(find_free_port)

# Write port to temp file so frontend/run.sh can discover it
echo "$PORT" > /tmp/spectra-backend-port

# Start the backend
echo ""
echo "🚀 Starting backend on http://localhost:$PORT"
if [ "$PORT" != "8080" ]; then
    echo "   ⚠️  Port 8080 was busy, using $PORT instead"
    echo "   Update frontend/.env.local if running frontend separately:"
    echo "   NEXT_PUBLIC_WS_URL=ws://localhost:$PORT/ws"
fi
echo "   Backend directory: $SCRIPT_DIR"
echo "   Press Ctrl+C to stop"
echo ""

# Set PYTHONPATH to current directory so 'app' module can be found
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH}"

# Run uvicorn from the backend directory
uvicorn app.main:app --reload --port "$PORT" --host 0.0.0.0
