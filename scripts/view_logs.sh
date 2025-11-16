#!/bin/bash

# SMART RADAR MVP - Log Viewer Script
# This script provides easy access to view different log files

# Set up directories
PROJECT_ROOT="$(dirname "$0")/.."
LOGS_DIR="$PROJECT_ROOT/logs"
BACKEND_LOGS_DIR="$PROJECT_ROOT/backend/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo "🔍 SMART RADAR MVP Log Viewer"
    echo ""
    echo "Usage: $0 [OPTION] [LOG_TYPE]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -f, --follow         Follow log file (like tail -f)"
    echo "  -l, --list           List all available log files"
    echo "  -e, --errors         Show only error logs"
    echo "  -t, --tail [n]       Show last n lines (default: 100)"
    echo "  -g, --grep PATTERN   Search for pattern in logs"
    echo ""
    echo "Log Types:"
    echo "  collectors           Collector debug logs"
    echo "  celery-worker        Celery worker logs"
    echo "  celery-beat          Celery beat scheduler logs"
    echo "  api                  FastAPI server logs"
    echo "  errors               Error-only logs"
    echo "  main                 Main application logs"
    echo "  all                  All logs combined"
    echo ""
    echo "Examples:"
    echo "  $0 collectors                    # View collectors log"
    echo "  $0 -f celery-worker             # Follow celery worker log"
    echo "  $0 -t 50 api                    # Show last 50 lines of API log"
    echo "  $0 -g \"FacebookCollector\" collectors  # Search for FacebookCollector in collectors log"
    echo "  $0 -e                           # Show all error logs"
    echo ""
}

# Function to list available log files
list_logs() {
    echo "📋 Available Log Files:"
    echo ""
    
    if [ -d "$BACKEND_LOGS_DIR" ]; then
        echo -e "${BLUE}Backend Logs:${NC}"
        find "$BACKEND_LOGS_DIR" -name "*.log" -type f -exec basename {} \; | sort | sed 's/^/  • /'
        echo ""
    fi
    
    if [ -d "$LOGS_DIR" ]; then
        echo -e "${BLUE}Main Logs:${NC}"
        find "$LOGS_DIR" -name "*.log" -type f -exec basename {} \; | sort | sed 's/^/  • /'
        echo ""
    fi
    
    echo -e "${BLUE}Recent Log Files (by modification time):${NC}"
    (
        find "$BACKEND_LOGS_DIR" -name "*.log" -type f -printf "%T@ %p\n" 2>/dev/null
        find "$LOGS_DIR" -name "*.log" -type f -printf "%T@ %p\n" 2>/dev/null
    ) | sort -rn | head -10 | while read timestamp file; do
        local basename_file=$(basename "$file")
        local mod_time=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -r "$timestamp" "+%Y-%m-%d %H:%M:%S")
        echo "  • $basename_file ($mod_time)"
    done
}

# Function to get log file path
get_log_file() {
    local log_type="$1"
    
    case "$log_type" in
        "collectors")
            echo "$BACKEND_LOGS_DIR/collectors.log"
            ;;
        "celery-worker")
            find "$BACKEND_LOGS_DIR" -name "celery_worker*.log" -type f | head -1
            ;;
        "celery-beat")
            find "$BACKEND_LOGS_DIR" -name "celery_beat*.log" -type f | head -1
            ;;
        "api")
            echo "$BACKEND_LOGS_DIR/api.log"
            ;;
        "errors")
            echo "$BACKEND_LOGS_DIR/errors.log"
            ;;
        "main")
            echo "$BACKEND_LOGS_DIR/smart_radar.log"
            ;;
        *)
            # Try to find file by pattern
            local found_file
            found_file=$(find "$BACKEND_LOGS_DIR" "$LOGS_DIR" -name "*$log_type*.log" -type f | head -1)
            if [ -n "$found_file" ]; then
                echo "$found_file"
            else
                echo ""
            fi
            ;;
    esac
}

# Function to view log with syntax highlighting
view_log() {
    local file="$1"
    local lines="$2"
    local follow="$3"
    local grep_pattern="$4"
    
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Log file not found: $file${NC}"
        return 1
    fi
    
    echo -e "${GREEN}📖 Viewing: $file${NC}"
    echo -e "${YELLOW}📊 File size: $(du -h "$file" | cut -f1)${NC}"
    echo ""
    
    local cmd
    if [ "$follow" = "true" ]; then
        cmd="tail -f"
    elif [ -n "$lines" ]; then
        cmd="tail -n $lines"
    else
        cmd="cat"
    fi
    
    if [ -n "$grep_pattern" ]; then
        $cmd "$file" | grep --color=always -i "$grep_pattern"
    else
        # Basic syntax highlighting for logs
        $cmd "$file" | sed -E \
            -e "s/ERROR/$(printf '\033[1;31m')&$(printf '\033[0m')/g" \
            -e "s/WARNING/$(printf '\033[1;33m')&$(printf '\033[0m')/g" \
            -e "s/INFO/$(printf '\033[1;32m')&$(printf '\033[0m')/g" \
            -e "s/DEBUG/$(printf '\033[1;36m')&$(printf '\033[0m')/g" \
            -e "s/❌/$(printf '\033[1;31m')&$(printf '\033[0m')/g" \
            -e "s/✅/$(printf '\033[1;32m')&$(printf '\033[0m')/g" \
            -e "s/⚠️/$(printf '\033[1;33m')&$(printf '\033[0m')/g" \
            -e "s/🔍/$(printf '\033[1;34m')&$(printf '\033[0m')/g"
    fi
}

# Function to show all error logs
show_errors() {
    echo -e "${RED}🚨 Error Logs from All Sources:${NC}"
    echo ""
    
    # Check all log files for errors
    local log_files=(
        "$BACKEND_LOGS_DIR/collectors.log"
        "$BACKEND_LOGS_DIR/celery.log"
        "$BACKEND_LOGS_DIR/api.log"
        "$BACKEND_LOGS_DIR/errors.log"
        "$BACKEND_LOGS_DIR/smart_radar.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            local error_count=$(grep -c -i "error\|exception\|❌" "$log_file" 2>/dev/null || echo "0")
            if [ "$error_count" -gt 0 ]; then
                echo -e "${YELLOW}📁 $(basename "$log_file") ($error_count errors):${NC}"
                grep -i "error\|exception\|❌" "$log_file" | tail -10 | sed 's/^/  /'
                echo ""
            fi
        fi
    done
}

# Function to view all logs combined
view_all_logs() {
    local lines="$1"
    local follow="$2"
    
    echo -e "${BLUE}📚 Combined Logs View${NC}"
    echo ""
    
    local log_files=()
    
    # Find all log files
    while IFS= read -r -d '' file; do
        log_files+=("$file")
    done < <(find "$BACKEND_LOGS_DIR" "$LOGS_DIR" -name "*.log" -type f -print0 2>/dev/null)
    
    if [ ${#log_files[@]} -eq 0 ]; then
        echo -e "${RED}❌ No log files found${NC}"
        return 1
    fi
    
    # Sort by modification time and combine
    printf '%s\n' "${log_files[@]}" | xargs ls -t | head -5 | while read file; do
        echo -e "${CYAN}=== $(basename "$file") ===${NC}"
        if [ -n "$lines" ]; then
            tail -n "$lines" "$file" 2>/dev/null
        else
            tail -n 20 "$file" 2>/dev/null
        fi
        echo ""
    done
}

# Parse command line arguments
FOLLOW=false
LINES=""
GREP_PATTERN=""
SHOW_ERRORS=false
LOG_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            list_logs
            exit 0
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                LINES="$2"
                shift 2
            else
                LINES="100"
                shift
            fi
            ;;
        -g|--grep)
            GREP_PATTERN="$2"
            shift 2
            ;;
        -e|--errors)
            SHOW_ERRORS=true
            shift
            ;;
        *)
            LOG_TYPE="$1"
            shift
            ;;
    esac
done

# Main logic
if [ "$SHOW_ERRORS" = "true" ]; then
    show_errors
    exit 0
fi

if [ -z "$LOG_TYPE" ]; then
    if [ "$FOLLOW" = "true" ] || [ -n "$LINES" ] || [ -n "$GREP_PATTERN" ]; then
        echo -e "${RED}❌ Please specify a log type${NC}"
        echo ""
        show_help
        exit 1
    else
        view_all_logs "$LINES" "$FOLLOW"
        exit 0
    fi
fi

if [ "$LOG_TYPE" = "all" ]; then
    view_all_logs "$LINES" "$FOLLOW"
    exit 0
fi

# Get specific log file
LOG_FILE=$(get_log_file "$LOG_TYPE")

if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}❌ Log file not found for type: $LOG_TYPE${NC}"
    echo ""
    echo "Available log types:"
    list_logs
    exit 1
fi

# View the log
view_log "$LOG_FILE" "$LINES" "$FOLLOW" "$GREP_PATTERN"