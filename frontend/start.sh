#!/bin/bash

# Start Spectra Frontend
# Run this from anywhere - it will navigate to the correct directory

set -e

echo "⚛️  Starting Spectra Frontend..."
echo ""

# Navigate to the frontend directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 Working directory: $SCRIPT_DIR"

# Check if we're in the frontend directory
if [ ! -f "package.json" ] || [ ! -d "src" ]; then
    echo "❌ Error: Frontend files not found in $SCRIPT_DIR"
    exit 1
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local file not found"
    echo "   Copy .env.local.example to .env.local:"
    echo "   cp .env.local.example .env.local"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
fi

# Kill any process on port 3000
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    echo "🛑 Killing existing process on port 3000 (PID: $FRONTEND_PID)"
    kill -9 $FRONTEND_PID 2>/dev/null || true
    sleep 2
fi

# Start the frontend
echo ""
echo "🚀 Starting frontend on http://localhost:3000"
echo "   Frontend directory: $SCRIPT_DIR"
echo "   Press Ctrl+C to stop"
echo ""

npm run dev
