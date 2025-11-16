#!/bin/bash

# SMART RADAR MVP - Background Services Startup Script
# This script starts all necessary background services for automated data collection

echo "🚀 Starting SMART RADAR MVP Background Services..."

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$0")/logs"
mkdir -p "$(dirname "$0")/backend/logs"

# Load environment variables from .env file
if [ -f "$(dirname "$0")/backend/.env" ]; then
    echo "📋 Loading environment variables from backend/.env..."
    export $(grep -v '^#' "$(dirname "$0")/backend/.env" | xargs)
else
    echo "⚠️  Warning: backend/.env file not found"
fi

# Set log file paths
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="$(dirname "$0")/logs"
BACKEND_LOG_DIR="$(dirname "$0")/backend/logs"

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