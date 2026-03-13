#!/bin/bash

# Start Spectra Backend
# Run this from the backend directory

set -e

echo "🐍 Starting Spectra Backend..."
echo ""

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    echo "   cd backend && ./start-backend.sh"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and add your API key"
    exit 1
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".venv/installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt --quiet
    touch .venv/installed
fi

# Kill any process on port 8080
BACKEND_PID=$(lsof -ti:8080 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    echo "🛑 Killing existing process on port 8080 (PID: $BACKEND_PID)"
    kill -9 $BACKEND_PID 2>/dev/null || true
    sleep 1
fi

echo "✅ Starting backend on http://localhost:8080"
echo ""

# Set PYTHONPATH to current directory so 'app' module can be found
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start uvicorn
uvicorn app.main:app --reload --port 8080 --host 0.0.0.0
