#!/bin/bash

# NewsIt SQS Consumer Startup Script
# Manages the NewsIt SQS consumer background worker

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_SCRIPT="$SCRIPT_DIR/workers/newsit_consumer.py"
PID_FILE="$SCRIPT_DIR/newsit_consumer.pid"
LOG_FILE="$SCRIPT_DIR/logs/newsit_consumer.log"
LOG_DIR="$SCRIPT_DIR/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if consumer is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is not running
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start the consumer
start_consumer() {
    print_info "Starting NewsIt SQS Consumer..."

    # Check if already running
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_warning "Consumer is already running (PID: $PID)"
        return 1
    fi

    # Create logs directory if it doesn't exist
    mkdir -p "$LOG_DIR"

    # Check if worker script exists
    if [ ! -f "$WORKER_SCRIPT" ]; then
        print_error "Worker script not found: $WORKER_SCRIPT"
        return 1
    fi

    # Check if .env file exists
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        print_warning ".env file not found. Make sure AWS_SQS_QUEUE_URL is configured."
    fi

    # Start the worker in background
    cd "$SCRIPT_DIR" || exit 1

    # Try to use uv if available, otherwise use python3
    if command -v uv &> /dev/null; then
        print_info "Using uv to run worker..."
        nohup uv run python "$WORKER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
        print_info "Using virtual environment..."
        source "$SCRIPT_DIR/.venv/bin/activate"
        nohup python "$WORKER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    else
        print_info "Using system Python..."
        nohup python3 "$WORKER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    fi

    PID=$!
    echo $PID > "$PID_FILE"

    # Wait a moment and check if process started successfully
    sleep 2
    if is_running; then
        print_success "NewsIt SQS Consumer started successfully (PID: $PID)"
        print_info "Logs: $LOG_FILE"
        return 0
    else
        print_error "Failed to start consumer. Check logs: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the consumer
stop_consumer() {
    print_info "Stopping NewsIt SQS Consumer..."

    if ! is_running; then
        print_warning "Consumer is not running"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    print_info "Sending SIGTERM to process $PID..."
    kill -TERM "$PID" 2>/dev/null

    # Wait for graceful shutdown (max 10 seconds)
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            print_success "Consumer stopped successfully"
            return 0
        fi
        sleep 1
    done

    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warning "Process didn't stop gracefully, forcing..."
        kill -9 "$PID" 2>/dev/null
        sleep 1
    fi

    rm -f "$PID_FILE"
    print_success "Consumer stopped"
    return 0
}

# Function to restart the consumer
restart_consumer() {
    print_info "Restarting NewsIt SQS Consumer..."
    stop_consumer
    sleep 2
    start_consumer
}

# Function to check status
status_consumer() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_success "NewsIt SQS Consumer is running (PID: $PID)"

        # Show process info
        ps -p "$PID" -o pid,ppid,cmd,%cpu,%mem,etime

        # Show last few log lines
        if [ -f "$LOG_FILE" ]; then
            echo ""
            print_info "Last 10 log lines:"
            tail -n 10 "$LOG_FILE"
        fi
        return 0
    else
        print_warning "NewsIt SQS Consumer is not running"
        return 1
    fi
}

# Function to show logs
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "Log file not found: $LOG_FILE"
        return 1
    fi

    # If -f flag is provided, follow the logs
    if [ "$1" == "-f" ] || [ "$1" == "--follow" ]; then
        print_info "Following logs (Ctrl+C to stop)..."
        tail -f "$LOG_FILE"
    else
        # Show last 50 lines
        print_info "Showing last 50 log lines:"
        tail -n 50 "$LOG_FILE"
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
${BLUE}NewsIt SQS Consumer Management Script${NC}

Usage: $0 {start|stop|restart|status|logs}

Commands:
  start     Start the NewsIt SQS consumer
  stop      Stop the NewsIt SQS consumer
  restart   Restart the NewsIt SQS consumer
  status    Show consumer status and recent logs
  logs      Show consumer logs
  logs -f   Follow consumer logs in real-time

Files:
  PID:    $PID_FILE
  Logs:   $LOG_FILE
  Worker: $WORKER_SCRIPT

Environment:
  Configure AWS_SQS_QUEUE_URL in .env file

EOF
}

# Main script logic
case "$1" in
    start)
        start_consumer
        ;;
    stop)
        stop_consumer
        ;;
    restart)
        restart_consumer
        ;;
    status)
        status_consumer
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

exit $?
