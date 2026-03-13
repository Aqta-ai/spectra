#!/bin/bash

# Start Spectra Frontend
# Run this from the frontend directory

set -e

echo "⚛️  Starting Spectra Frontend..."
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the frontend directory"
    echo "   cd frontend && ./start-frontend.sh"
    exit 1
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local file not found"
    echo "   Copy .env.local.example to .env.local"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Kill any process on port 3000
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    echo "🛑 Killing existing process on port 3000 (PID: $FRONTEND_PID)"
    kill -9 $FRONTEND_PID 2>/dev/null || true
    sleep 1
fi

echo "✅ Starting frontend on http://localhost:3000"
echo ""

# Start Next.js dev server
npm run dev
