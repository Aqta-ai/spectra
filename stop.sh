#!/bin/bash

# Spectra Stop Script
# Stops all running Spectra processes

echo "🛑 Stopping Spectra..."
echo ""

# Read the port the backend is actually running on
BACKEND_PORT=$(cat /tmp/spectra-backend-port 2>/dev/null || echo "8080")

# Stop backend on its actual port, plus scan the full range just in case
for port in $BACKEND_PORT 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089; do
    PIDS=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "Stopping process on port $port..."
        kill -9 $PIDS 2>/dev/null
    fi
done
echo "✅ Backend stopped"

# Stop frontend (port 3000)
FRONTEND_PIDS=$(lsof -ti:3000 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "Stopping frontend processes on port 3000..."
    kill -9 $FRONTEND_PIDS 2>/dev/null
    echo "✅ Frontend stopped"
else
    echo "ℹ️  No frontend process found on port 3000"
fi

# Clean up
rm -f /tmp/spectra-backend-port

echo ""
echo "✅ All Spectra processes stopped"
