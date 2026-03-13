#!/bin/bash

# Spectra Diagnostic Script
# Checks your environment and helps troubleshoot issues

echo "🔍 Spectra Diagnostic Tool"
echo "=========================="
echo ""

# Check if we're in the spectra directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the spectra directory"
    exit 1
fi

# Check Python
echo "Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
else
    echo "❌ Python 3 not found"
fi

# Check Node
echo "Checking Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js $NODE_VERSION"
else
    echo "❌ Node.js not found"
fi

# Check npm
echo "Checking npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✅ npm $NPM_VERSION"
else
    echo "❌ npm not found"
fi

# Check backend virtual environment
echo ""
echo "Checking backend..."
if [ -d "backend/.venv" ]; then
    echo "✅ Virtual environment exists"
    
    # Check if dependencies are installed
    if [ -f "backend/.venv/installed" ]; then
        echo "✅ Dependencies installed"
    else
        echo "⚠️  Dependencies may not be installed"
        echo "   Run: cd backend && source .venv/bin/activate && pip install -r requirements.txt"
    fi
else
    echo "❌ Virtual environment not found"
    echo "   Run: cd backend && python3 -m venv .venv"
fi

# Check backend .env
if [ -f "backend/.env" ]; then
    echo "✅ backend/.env exists"
    
    # Check if API key is set
    if grep -q "GOOGLE_API_KEY=your_api_key_here" backend/.env; then
        echo "⚠️  API key not configured (still has placeholder)"
        echo "   Edit backend/.env and add your Gemini API key"
    elif grep -q "GOOGLE_API_KEY=" backend/.env; then
        echo "✅ API key configured"
    else
        echo "⚠️  API key not found in .env"
    fi
else
    echo "❌ backend/.env not found"
    echo "   Run: cp backend/.env.example backend/.env"
fi

# Check frontend node_modules
echo ""
echo "Checking frontend..."
if [ -d "frontend/node_modules" ]; then
    echo "✅ Node modules installed"
else
    echo "❌ Node modules not found"
    echo "   Run: cd frontend && npm install"
fi

# Check frontend .env.local
if [ -f "frontend/.env.local" ]; then
    echo "✅ frontend/.env.local exists"
else
    echo "❌ frontend/.env.local not found"
    echo "   Run: cp frontend/.env.local.example frontend/.env.local"
fi

# Check ports
echo ""
echo "Checking ports..."
BACKEND_PID=$(lsof -ti:8080 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    echo "⚠️  Port 8080 is in use (PID: $BACKEND_PID)"
    echo "   Run: ./stop.sh or ./kill-ports.sh"
else
    echo "✅ Port 8080 is available"
fi

FRONTEND_PID=$(lsof -ti:3000 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    echo "⚠️  Port 3000 is in use (PID: $FRONTEND_PID)"
    echo "   Run: ./stop.sh or ./kill-ports.sh"
else
    echo "✅ Port 3000 is available"
fi

# Check app directory structure
echo ""
echo "Checking backend structure..."
if [ -d "backend/app" ]; then
    echo "✅ backend/app directory exists"
    
    if [ -f "backend/app/__init__.py" ]; then
        echo "✅ backend/app/__init__.py exists"
    else
        echo "❌ backend/app/__init__.py missing"
    fi
    
    if [ -f "backend/app/main.py" ]; then
        echo "✅ backend/app/main.py exists"
    else
        echo "❌ backend/app/main.py missing"
    fi
else
    echo "❌ backend/app directory not found"
fi

# Summary
echo ""
echo "=========================="
echo "Diagnostic complete!"
echo ""
echo "To start Spectra:"
echo "  ./run.sh"
echo ""
echo "Or manually:"
echo "  Terminal 1: cd backend && ./start.sh"
echo "  Terminal 2: cd frontend && ./start.sh"
echo ""
