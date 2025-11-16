#!/bin/bash

# SMART RADAR MVP - Simple Startup Script
# Usage: ./start_simple.sh [start|stop|restart]

ACTION=${1:-start}

stop_services() {
    echo "🛑 Stopping all SMART RADAR services..."
    pkill -f "uvicorn.*main:app" || true
    pkill -f "celery.*worker" || true
    pkill -f "celery.*beat" || true
    pkill -f "vite.*frontend" || true
    echo "✅ All services stopped"
}

start_services() {
    echo "🚀 Starting SMART RADAR Services..."

    # Stop any existing instances
    echo "🛑 Stopping any running instances..."
    stop_services

    # Create logs directory
    mkdir -p logs

    # Navigate to backend
    cd "$(dirname "$0")/backend"

    # Load environment variables
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi

    # Start backend server
    echo "🌐 Starting FastAPI backend..."
    uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!

    # Start Celery worker with all required queues
    echo "🔧 Starting Celery worker..."
    uv run celery -A app.core.celery_app worker --loglevel=info --queues=default,data_collection,intelligence,monitoring --concurrency=4 > ../logs/celery_worker.log 2>&1 &
    WORKER_PID=$!

    # Start Celery beat
    echo "⏰ Starting Celery beat..."
    uv run celery -A app.core.celery_app beat --loglevel=info > ../logs/celery_beat.log 2>&1 &
    BEAT_PID=$!

    # Navigate to frontend
    cd ../frontend

    # Start frontend
    echo "⚛️  Starting Vue.js frontend..."
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!

    echo ""
    echo "✅ All services started in background!"
    echo ""
    echo "📊 Frontend: http://localhost:5173"
    echo "🔌 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "📋 Logs: logs/ directory"
    echo "🛑 To stop: ./start_simple.sh stop"
    echo ""
    echo "Process IDs:"
    echo "  Backend: $BACKEND_PID"
    echo "  Celery Worker: $WORKER_PID"
    echo "  Celery Beat: $BEAT_PID"
    echo "  Frontend: $FRONTEND_PID"
    echo ""
}

# Main script logic
case "$ACTION" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        echo "🔄 Restarting SMART RADAR services..."
        stop_services
        sleep 2
        start_services
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        echo ""
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Stop and restart all services"
        exit 1
        ;;
esac
