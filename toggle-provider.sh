#!/bin/bash
# Simple provider toggle: switches between Gemini Live and Ollama offline mode

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Get current provider from .env
CURRENT_PROVIDER=$(grep "^SPECTRA_PROVIDER=" "$REPO_ROOT/backend/.env" | cut -d'=' -f2 | xargs)

if [ "$CURRENT_PROVIDER" = "ollama" ]; then
    NEW_PROVIDER="gemini"
    echo "Switching from Ollama → Gemini Live"
else
    NEW_PROVIDER="ollama"
    echo "Switching from Gemini Live → Ollama"
fi

# Update .env
sed -i '' "s/^SPECTRA_PROVIDER=.*/SPECTRA_PROVIDER=$NEW_PROVIDER/" "$REPO_ROOT/backend/.env"

# Kill existing processes
echo "Stopping current services..."
pkill -f "uvicorn|next dev" 2>/dev/null || true
sleep 2

# Restart with new provider
cd "$REPO_ROOT"
if [ "$NEW_PROVIDER" = "ollama" ]; then
    echo "Starting Ollama mode..."
    ./run-offline.sh ollama
else
    echo "Starting Gemini Live mode..."
    ./run.sh
fi
