#!/bin/bash

# SMART RADAR MVP - Background Services Startup Script (Ubuntu)
# This script starts all necessary background services for automated data collection on Ubuntu

echo "🚀 Starting SMART RADAR MVP Background Services (Ubuntu)..."

# Create logs directory if it doesn't exist
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/backend/logs"

# Set log file paths
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_LOG_DIR="$SCRIPT_DIR/backend/logs"

# Function to check if Node.js and npm are available
check_nodejs() {
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Please install Node.js first:"
        echo "   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -"
        echo "   sudo apt-get install -y nodejs"
        exit 1
    fi

    if ! command -v npm &> /dev/null; then
        echo "❌ npm not found. Please install npm first:"
        echo "   sudo apt install -y npm"
        exit 1
    fi
}

# Function to check if Python and uv are available
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 not found. Please install Python3 first:"
        echo "   sudo apt update && sudo apt install -y python3 python3-pip"
        exit 1
    fi

    if ! command -v uv &> /dev/null; then
        echo "❌ uv not found. Please install uv first:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "   source ~/.local/bin/env"
        exit 1
    fi
}

# Function to check if MongoDB is running
check_mongodb() {
    # Check if MongoDB is available (either locally or via Docker)
    if ! command -v mongosh &> /dev/null && ! docker ps | grep -q mongo; then
        echo "⚠️  MongoDB not detected. Make sure MongoDB is running via Docker:"
        echo "   docker run -d -p 27017:27017 --name mongodb \\"
        echo "     -e MONGO_INITDB_ROOT_USERNAME=admin \\"
        echo "     -e MONGO_INITDB_ROOT_PASSWORD=password \\"
        echo "     mongo:7.0"
        echo ""
        echo "Or install MongoDB locally:"
        echo "   https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/"
        echo ""
        echo "Continuing anyway - MongoDB connection will be tested by the backend..."
    fi
}

# Run all checks
echo "🔍 Checking system requirements..."
check_nodejs
check_python
check_mongodb

# Load environment variables from .env file
if [ -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "📋 Loading environment variables from backend/.env..."
    export $(grep -v '^#' "$SCRIPT_DIR/backend/.env" | xargs)
else
    echo "⚠️  Warning: backend/.env file not found"
fi

# Navigate to backend directory
cd "$(dirname "$0")/backend"

echo "🔧 Starting Celery Worker..."
uv run --no-project celery -A app.core.celery_instance worker --loglevel=debug \
  --concurrency=4 \
  --queues=default,data_collection,intelligence,monitoring \
  --logfile="$BACKEND_LOG_DIR/celery_worker_$TIMESTAMP.log" \
  --pidfile="$LOG_DIR/celery_worker.pid" &
WORKER_PID=$!

echo "⏰ Starting Celery Beat Scheduler..."
uv run --no-project celery -A app.core.celery_instance beat --loglevel=debug \
  --logfile="$BACKEND_LOG_DIR/celery_beat_$TIMESTAMP.log" \
  --pidfile="$LOG_DIR/celery_beat.pid" &
BEAT_PID=$!

echo "📊 Starting Celery Flower Monitoring Dashboard..."
uv run --no-project celery -A app.core.celery_instance flower --port=5555 \
  --basic_auth=admin:smartradar2024 \
  > "$LOG_DIR/flower_$TIMESTAMP.log" 2>&1 &
FLOWER_PID=$!

echo "🌐 Starting FastAPI Backend Server..."
uv run --no-project uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
  --log-level debug \
  --access-log \
  > "$LOG_DIR/fastapi_$TIMESTAMP.log" 2>&1 &
API_PID=$!

# Navigate to frontend directory
cd "../frontend"

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

echo "⚛️ Starting Vue.js Frontend..."
npm run dev > "$LOG_DIR/frontend_$TIMESTAMP.log" 2>&1 &
FRONTEND_PID=$!

echo ""
echo "✅ All services started successfully!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API Server: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🌸 Celery Flower: http://localhost:5555 (admin/smartradar2024)"
echo ""
echo "📈 Automated Data Collection Schedule:"
echo "   • Every 30 minutes: Social media data collection"
echo "   • Every 15 minutes: Intelligence processing"
echo "   • Every 5 minutes: Threat monitoring"
echo ""
echo "📋 Log Files Location:"
echo "   • Main logs: $LOG_DIR/"
echo "   • Backend logs: $BACKEND_LOG_DIR/"
echo "   • Collectors: $BACKEND_LOG_DIR/collectors.log"
echo "   • Celery Worker: $BACKEND_LOG_DIR/celery_worker_$TIMESTAMP.log"
echo "   • Celery Beat: $BACKEND_LOG_DIR/celery_beat_$TIMESTAMP.log"
echo "   • FastAPI: $LOG_DIR/fastapi_$TIMESTAMP.log"
echo "   • Frontend: $LOG_DIR/frontend_$TIMESTAMP.log"
echo ""
echo "🔧 System Information:"
echo "   • Python version: $(python3 --version)"
echo "   • Node.js version: $(node --version)"
echo "   • npm version: $(npm --version)"
echo ""
echo "🛑 To stop all services, press Ctrl+C"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $WORKER_PID $BEAT_PID $FLOWER_PID $API_PID $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script termination
trap cleanup SIGINT SIGTERM

# Wait for all background processes
wait