#!/bin/bash

# Kill processes on Spectra ports (8080-8089 for backend, 3000 for frontend)

echo "🔍 Checking for Spectra processes..."

# Check backend ports 8080-8089
for port in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089; do
    PID=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo "🛑 Killing process on port $port (PID: $PID)"
        kill -9 $PID 2>/dev/null || echo "   Process already stopped"
        sleep 0.5
    fi
done

# Check port 3000 (frontend)
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    echo "🛑 Killing process on port 3000 (PID: $FRONTEND_PID)"
    kill -9 $FRONTEND_PID 2>/dev/null || echo "   Process already stopped"
    sleep 1
else
    echo "✅ Port 3000 is free"
fi

# Clean up port file
rm -f /tmp/spectra-backend-port

echo ""
echo "✅ Ports are now available. You can start Spectra."
