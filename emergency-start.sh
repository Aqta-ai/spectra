#!/bin/bash

echo "🚨 EMERGENCY SPECTRA - DEADLINE MODE 🚨"
echo ""
echo "🔥 Starting simplified Spectra that WORKS immediately"
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend: http://localhost:8080"
echo ""

# Kill any existing processes
./kill-ports.sh

# Start emergency backend
echo "🚀 Starting emergency backend..."
python3 emergency-fix.py &
BACKEND_PID=$!

# Start frontend
echo "🚀 Starting frontend..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ EMERGENCY SPECTRA IS RUNNING!"
echo ""
echo "🎯 QUICK TEST:"
echo "1. Go to http://localhost:3000"
echo "2. Click 'Connect'"
echo "3. Type: 'Hello Spectra'"
echo "4. She will respond immediately!"
echo ""
echo "🛑 To stop: Ctrl+C or kill $BACKEND_PID $FRONTEND_PID"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID