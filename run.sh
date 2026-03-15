#!/bin/bash

# Spectra Run Script — starts backend + frontend simultaneously

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colours
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}🔮 Starting Spectra...${NC}"
echo ""

# Make scripts executable
chmod +x backend/start.sh frontend/start.sh kill-ports.sh stop.sh 2>/dev/null || true

# Kill existing processes
echo -e "${YELLOW}🧹 Cleaning up existing processes...${NC}"
./kill-ports.sh

# Prerequisites
echo ""
echo -e "${YELLOW}✅ Checking prerequisites...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"; exit 1
fi
echo "  ✓ Python 3 found ($(python3 --version))"

if ! command -v node &>/dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"; exit 1
fi
echo "  ✓ Node.js found ($(node --version))"

# Check API key configuration
if [ -f "backend/.env" ]; then
    if grep -q "GOOGLE_API_KEY=" backend/.env && ! grep -q "GOOGLE_API_KEY=$" backend/.env && ! grep -q "GOOGLE_API_KEY=\"\"" backend/.env; then
        echo "  ✓ API key configured"
    else
        echo -e "${YELLOW}⚠️  GOOGLE_API_KEY not set in backend/.env${NC}"
        echo "     Add your Google AI Studio API key to backend/.env"
    fi
else
    echo -e "${RED}❌ backend/.env not found${NC}"
    echo "   cp backend/.env.example backend/.env  — then add your GOOGLE_API_KEY"
    exit 1
fi

if [ ! -f "frontend/.env.local" ]; then
    echo -e "${YELLOW}⚠️  frontend/.env.local not found, creating from example...${NC}"
    cp frontend/.env.local.example frontend/.env.local
fi
echo "  ✓ frontend/.env.local found"

# Log files
BACKEND_LOG="/tmp/spectra-backend.log"
FRONTEND_LOG="/tmp/spectra-frontend.log"
> "$BACKEND_LOG"
> "$FRONTEND_LOG"

# Find a free port for the backend (8080–8089)
find_free_port() {
  for port in 8080 8081 8082 8083 8084 8085 8086 8087 8088 8089; do
    if ! lsof -ti:$port &>/dev/null; then
      echo $port
      return
    fi
  done
  echo -e "${RED}❌ No free port found in range 8080-8089${NC}"
  exit 1
}

BACKEND_PORT=$(find_free_port)
echo "$BACKEND_PORT" > /tmp/spectra-backend-port

echo ""
echo -e "${CYAN}🚀 Starting backend + frontend in parallel...${NC}"
if [ "$BACKEND_PORT" != "8080" ]; then
    echo -e "${YELLOW}   ⚠️  Port 8080 busy — backend will use port ${BACKEND_PORT}${NC}"
fi
echo ""

# ── Backend ──────────────────────────────────────────────────────────────────
(
  cd "$SCRIPT_DIR/backend"
  [ ! -d ".venv" ] && python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip --quiet
  pip install -r requirements.txt --quiet
  export PYTHONPATH="$SCRIPT_DIR/backend:${PYTHONPATH}"
  exec uvicorn app.main:app --reload --port "$BACKEND_PORT" --host 0.0.0.0
) >> "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# ── Frontend (uses the backend port we just picked) ──────────────────────────
(
  cd "$SCRIPT_DIR/frontend"
  [ ! -d "node_modules" ] && npm install --silent
  export NEXT_PUBLIC_WS_URL="ws://localhost:${BACKEND_PORT}/ws"
  exec npm run dev
) >> "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

echo -e "  Backend  PID ${BACKEND_PID}  → logs: ${BACKEND_LOG}"
echo -e "  Frontend PID ${FRONTEND_PID}  → logs: ${FRONTEND_LOG}"
echo ""

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services...${NC}"
BACKEND_READY=0; FRONTEND_READY=0
for i in $(seq 1 60); do
    if [ $BACKEND_READY -eq 0 ] && curl -s "http://localhost:${BACKEND_PORT}/health" &>/dev/null; then
        echo -e "  ${GREEN}✓ Backend ready${NC}  http://localhost:${BACKEND_PORT}"
        BACKEND_READY=1
    fi
    if [ $FRONTEND_READY -eq 0 ] && curl -s http://localhost:3000 &>/dev/null; then
        echo -e "  ${GREEN}✓ Frontend ready${NC} http://localhost:3000"
        FRONTEND_READY=1
    fi
    [ $BACKEND_READY -eq 1 ] && [ $FRONTEND_READY -eq 1 ] && break
    sleep 1
done

echo ""
if [ $BACKEND_READY -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Backend may still be starting — check logs: tail -f $BACKEND_LOG${NC}"
fi
if [ $FRONTEND_READY -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Frontend may still be starting — check logs: tail -f $FRONTEND_LOG${NC}"
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  🌐 Open: ${GREEN}http://localhost:3000${NC}"
echo -e "  🔌 Backend: ${GREEN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  🎤 Say ${CYAN}\"Hello Spectra\"${NC} or ${CYAN}\"Describe the screen\"${NC} to begin"
echo -e ""
echo -e "  📊 Monitor:"
echo -e "    Health: curl http://localhost:${BACKEND_PORT}/health"
echo -e "    Vision: curl http://localhost:${BACKEND_PORT}/vision-debug"
echo -e ""
echo -e "  📝 Logs:"
echo -e "    tail -f $BACKEND_LOG"
echo -e "    tail -f $FRONTEND_LOG"
echo -e ""
echo -e "  🛑 Stop: ${YELLOW}./stop.sh${NC}  or  Ctrl+C"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Trap Ctrl+C to kill both
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping Spectra...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# Tail both logs to terminal
tail -f "$BACKEND_LOG" "$FRONTEND_LOG" &
TAIL_PID=$!

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
kill $TAIL_PID 2>/dev/null || true
