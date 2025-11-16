#!/bin/bash

# SMART RADAR MVP - Log Rotation Script
# This script rotates and compresses old log files to save disk space

# Set up directories
PROJECT_ROOT="$(dirname "$0")/.."
LOGS_DIR="$PROJECT_ROOT/logs"
BACKEND_LOGS_DIR="$PROJECT_ROOT/backend/logs"
ARCHIVE_DIR="$LOGS_DIR/archive"

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"

# Configuration
DAYS_TO_KEEP=30
COMPRESS_OLDER_THAN_DAYS=7

echo "🔄 Starting log rotation for SMART RADAR MVP..."
echo "📁 Logs directory: $LOGS_DIR"
echo "📁 Backend logs directory: $BACKEND_LOGS_DIR"
echo "📁 Archive directory: $ARCHIVE_DIR"
echo "📅 Keeping logs for: $DAYS_TO_KEEP days"
echo "🗜️ Compressing logs older than: $COMPRESS_OLDER_THAN_DAYS days"
echo ""

# Function to rotate logs in a directory
rotate_logs_in_dir() {
    local dir="$1"
    local description="$2"
    
    if [ ! -d "$dir" ]; then
        echo "⚠️ Directory not found: $dir"
        return
    fi
    
    echo "🔄 Processing $description logs in: $dir"
    
    # Count files
    local total_files=$(find "$dir" -name "*.log" -type f | wc -l)
    echo "   📊 Found $total_files log files"
    
    # Compress logs older than COMPRESS_OLDER_THAN_DAYS
    local compressed_count=0
    while IFS= read -r -d '' file; do
        if [ -f "$file" ] && [[ "$file" == *.log ]] && [[ "$file" != *.gz ]]; then
            local filename=$(basename "$file")
            local compressed_file="$ARCHIVE_DIR/${filename%.log}_$(date -r "$file" +%Y%m%d_%H%M%S).log.gz"
            
            echo "   🗜️ Compressing: $filename → $(basename "$compressed_file")"
            gzip -c "$file" > "$compressed_file"
            
            if [ $? -eq 0 ]; then
                rm "$file"
                ((compressed_count++))
                echo "   ✅ Compressed and removed: $filename"
            else
                echo "   ❌ Failed to compress: $filename"
            fi
        fi
    done < <(find "$dir" -name "*.log" -type f -mtime +$COMPRESS_OLDER_THAN_DAYS -print0)
    
    echo "   📦 Compressed $compressed_count files"
    
    # Remove very old compressed files
    local removed_count=0
    while IFS= read -r -d '' file; do
        echo "   🗑️ Removing old archive: $(basename "$file")"
        rm "$file"
        ((removed_count++))
    done < <(find "$ARCHIVE_DIR" -name "*.log.gz" -type f -mtime +$DAYS_TO_KEEP -print0)
    
    echo "   🗑️ Removed $removed_count old archives"
    echo ""
}

# Rotate logs in main directories
rotate_logs_in_dir "$LOGS_DIR" "Main"
rotate_logs_in_dir "$BACKEND_LOGS_DIR" "Backend"

# Clean up empty directories
echo "🧹 Cleaning up empty directories..."
find "$LOGS_DIR" -type d -empty -delete 2>/dev/null
find "$BACKEND_LOGS_DIR" -type d -empty -delete 2>/dev/null

# Display summary
echo "📊 Log Rotation Summary:"
echo "   📁 Main logs: $(find "$LOGS_DIR" -name "*.log" -type f | wc -l) active files"
echo "   📁 Backend logs: $(find "$BACKEND_LOGS_DIR" -name "*.log" -type f | wc -l) active files"
echo "   📦 Archived files: $(find "$ARCHIVE_DIR" -name "*.log.gz" -type f | wc -l) compressed files"

# Calculate disk usage
if command -v du >/dev/null 2>&1; then
    echo "   💾 Total logs disk usage: $(du -sh "$LOGS_DIR" 2>/dev/null | cut -f1)"
    echo "   💾 Backend logs disk usage: $(du -sh "$BACKEND_LOGS_DIR" 2>/dev/null | cut -f1)"
    echo "   💾 Archive disk usage: $(du -sh "$ARCHIVE_DIR" 2>/dev/null | cut -f1)"
fi

echo ""
echo "✅ Log rotation completed successfully!"
echo ""
echo "💡 To automate this script, add it to your crontab:"
echo "   # Run daily at 2 AM"
echo "   0 2 * * * $PROJECT_ROOT/scripts/rotate_logs.sh"
echo ""