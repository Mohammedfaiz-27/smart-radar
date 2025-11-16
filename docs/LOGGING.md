# SMART RADAR MVP - Logging Guide

This document explains the comprehensive logging system implemented for SMART RADAR MVP, including file locations, log rotation, and debugging procedures.

## 📁 Log File Structure

### Main Log Directory: `/logs/`
- **Purpose**: Application-level logs from all services
- **Files**:
  - `fastapi_YYYYMMDD_HHMMSS.log` - FastAPI server logs
  - `frontend_YYYYMMDD_HHMMSS.log` - Vue.js frontend logs

### Backend Log Directory: `/backend/logs/`
- **Purpose**: Backend-specific Python application logs
- **Files**:
  - `smart_radar.log` - Main application log (rotated)
  - `collectors.log` - Data collector debug logs (rotated)
  - `celery.log` - Celery worker and beat logs (rotated)
  - `api.log` - FastAPI endpoint logs (rotated)
  - `errors.log` - Error-only logs from all sources (rotated)
  - `celery_worker_YYYYMMDD_HHMMSS.log` - Worker session logs
  - `celery_beat_YYYYMMDD_HHMMSS.log` - Beat scheduler session logs

### Archive Directory: `/logs/archive/`
- **Purpose**: Compressed historical logs
- **Files**: `*.log.gz` - Compressed logs older than 7 days

## 🔧 Logging Configuration

### Log Levels
- **DEBUG**: Detailed debugging information (collectors, API calls, data processing)
- **INFO**: General application flow and important events
- **WARNING**: Warning conditions that should be monitored
- **ERROR**: Error conditions that need attention

### Automatic Log Rotation
- **Rotation**: Logs are automatically rotated when they reach 10-20MB
- **Compression**: Logs older than 7 days are compressed
- **Retention**: Compressed logs are kept for 30 days
- **Backup Count**: 5-10 backup files per log type

## 🚀 Getting Started with Logs

### Starting Services with Logging
```bash
# Start all services with comprehensive logging
./start_workers.sh

# The script will display log file locations:
# 📋 Log Files Location:
#    • Main logs: /path/to/logs/
#    • Backend logs: /path/to/backend/logs/
#    • Collectors: /path/to/backend/logs/collectors.log
#    • etc...
```

### Viewing Logs

#### Quick Log Viewer Script
```bash
# View available logs
./scripts/view_logs.sh --list

# View collector logs
./scripts/view_logs.sh collectors

# Follow celery worker logs in real-time
./scripts/view_logs.sh --follow celery-worker

# Search for specific patterns
./scripts/view_logs.sh --grep "FacebookCollector" collectors

# Show only errors from all logs
./scripts/view_logs.sh --errors

# Show last 50 lines
./scripts/view_logs.sh --tail 50 api
```

#### Manual Log Access
```bash
# Real-time collector debugging
tail -f backend/logs/collectors.log

# Search for errors in all logs
grep -r "ERROR\|❌" backend/logs/

# Monitor API requests
tail -f backend/logs/api.log | grep -i "post\|get"

# Check celery task execution
tail -f backend/logs/celery.log | grep -i "task"
```

## 📊 Log Content and Debugging

### Collector Logs (`collectors.log`)
Contains detailed debug information for each data collection platform:

```
2024-01-15 14:30:15 | collector.facebookcollector | DEBUG | 🔍 Facebook search for keyword: 'DMK' (Tamil: False)
2024-01-15 14:30:16 | collector.facebookcollector | DEBUG | 📄 Starting Facebook pagination (max_pages: 5, max_results: 100)
2024-01-15 14:30:17 | collector.facebookcollector | INFO  | ✅ [FACEBOOK][1234] API Success in 1.23s
2024-01-15 14:30:18 | collector.facebookcollector | DEBUG | 📊 Post engagement: 150 (reactions: 120, comments: 20, shares: 10, threshold: 5)
```

**Key Debug Information**:
- Search parameters and keyword analysis
- API request/response timing and status
- Engagement threshold filtering
- Pagination progress
- Tamil character detection
- Rate limiting delays
- Error context with request IDs

### Celery Logs (`celery.log`)
Shows background task execution:

```
2024-01-15 14:30:00 | celery.worker | INFO | Starting scheduled data collection
2024-01-15 14:30:01 | celery.task | DEBUG | Task: app.tasks.data_collection_tasks.collect_posts_for_cluster
2024-01-15 14:30:05 | celery.task | INFO | Task completed in 4.23s: 45 posts collected
```

### API Logs (`api.log`)
FastAPI endpoint requests and responses:

```
2024-01-15 14:30:10 | uvicorn.access | INFO | GET /api/v1/posts?cluster_type=own - 200
2024-01-15 14:30:11 | fastapi.router | DEBUG | Processing posts query: cluster_type=own, limit=50
```

### Error Logs (`errors.log`)
All error conditions across the application:

```
2024-01-15 14:30:20 | collector.xcollector | ERROR | ❌ [X][5678] API error: 429 after 2.15s
2024-01-15 14:30:21 | celery.task | ERROR | Task failed: Rate limit exceeded for X API
```

## 🛠️ Troubleshooting Common Issues

### Data Collection Problems

#### No Posts Being Collected
1. **Check collector logs**:
   ```bash
   ./scripts/view_logs.sh collectors
   ```

2. **Look for**:
   - API key configuration errors
   - Rate limiting messages
   - Network connectivity issues
   - Engagement threshold too high

#### Specific Platform Issues

**Facebook Collector**:
```bash
# Check Facebook-specific logs
./scripts/view_logs.sh --grep "FacebookCollector" collectors

# Common issues:
# - "🔑 Facebook API key not configured"
# - "❌ [FACEBOOK] API error: 401" (invalid credentials)
# - "⏳ [FACEBOOK] Rate limited" (too many requests)
```

**X (Twitter) Collector**:
```bash
# Check X-specific logs
./scripts/view_logs.sh --grep "XCollector" collectors

# Common issues:
# - Complex response structure parsing
# - Timeline entry filtering
# - Engagement calculation errors
```

**YouTube Collector**:
```bash
# Check YouTube-specific logs
./scripts/view_logs.sh --grep "YouTubeCollector" collectors

# Common issues:
# - Video statistics retrieval
# - Quota exceeded errors
# - Regional content restrictions
```

### Celery Task Issues

#### Tasks Not Running
1. **Check worker status**:
   ```bash
   ./scripts/view_logs.sh celery-worker
   ```

2. **Check beat scheduler**:
   ```bash
   ./scripts/view_logs.sh celery-beat
   ```

3. **Common problems**:
   - Redis connection issues
   - Task queue overload
   - Worker memory issues

### Performance Issues

#### High Memory Usage
```bash
# Monitor log file sizes
du -sh logs/ backend/logs/

# Check for excessive logging
./scripts/view_logs.sh --grep "DEBUG" collectors | wc -l
```

#### Slow API Responses
```bash
# Check API response times
./scripts/view_logs.sh --grep "API Success" collectors

# Look for timing patterns:
# "✅ [PLATFORM][ID] API Success in X.XXs"
```

## 🔄 Log Management

### Manual Log Rotation
```bash
# Run log rotation script
./scripts/rotate_logs.sh

# Output shows:
# 🔄 Starting log rotation for SMART RADAR MVP...
# 🗜️ Compressing logs older than 7 days
# 🗑️ Removing archives older than 30 days
```

### Automated Log Rotation
Add to crontab for automatic rotation:
```bash
# Edit crontab
crontab -e

# Add this line for daily rotation at 2 AM:
0 2 * * * /path/to/smart-radar/scripts/rotate_logs.sh
```

### Disk Space Monitoring
```bash
# Check total log disk usage
du -sh logs/ backend/logs/

# Monitor largest log files
find backend/logs/ logs/ -name "*.log" -exec du -h {} \; | sort -hr | head -10

# Clean up if needed
./scripts/rotate_logs.sh
```

## 📈 Log Analysis and Monitoring

### Performance Metrics
```bash
# Collection success rates by platform
grep "✅.*posts collected" backend/logs/collectors.log | grep "Facebook\|X\|YouTube"

# Average API response times
grep "API Success in" backend/logs/collectors.log | grep -o "[0-9]\+\.[0-9]\+s"

# Error rates
grep -c "ERROR\|❌" backend/logs/collectors.log
```

### Data Quality Monitoring
```bash
# Posts with high engagement
grep "Post engagement:" backend/logs/collectors.log | grep -o "engagement: [0-9]\+"

# Tamil content detection
grep "Tamil: true" backend/logs/collectors.log | wc -l

# Rate limiting frequency
grep "Rate limited" backend/logs/collectors.log | wc -l
```

### Real-time Monitoring
```bash
# Monitor all errors in real-time
tail -f backend/logs/errors.log

# Monitor collector activity
tail -f backend/logs/collectors.log | grep -E "🔍|✅|❌"

# Monitor task execution
tail -f backend/logs/celery.log | grep -E "Task|completed|failed"
```

## ⚙️ Configuration

### Environment Variables for Logging
```bash
# In backend/.env file:
DEBUG=true                    # Enable debug logging
LOG_LEVEL=DEBUG              # Set log level (DEBUG, INFO, WARNING, ERROR)
```

### Adjusting Log Levels
Modify `/backend/app/core/logging_config.py`:

```python
# For less verbose collector logs:
collectors_handler.setLevel(logging.INFO)

# For more detailed API logs:
api_handler.setLevel(logging.DEBUG)
```

### Custom Log Filters
Add custom filters to focus on specific components:

```python
# Example: Only log Tamil-related activities
class TamilFilter(logging.Filter):
    def filter(self, record):
        return 'tamil' in record.getMessage().lower()
```

## 🚨 Alerts and Notifications

### Setting Up Log Monitoring
Monitor for critical errors:

```bash
# Create alert script for critical errors
#!/bin/bash
ERROR_COUNT=$(grep -c "CRITICAL\|FATAL" backend/logs/errors.log)
if [ $ERROR_COUNT -gt 0 ]; then
    echo "🚨 CRITICAL ERRORS DETECTED: $ERROR_COUNT"
    # Send notification (email, Slack, etc.)
fi
```

### Log-based Health Checks
```bash
# Check if collectors are working
RECENT_COLLECTIONS=$(grep -c "posts collected" backend/logs/collectors.log)
if [ $RECENT_COLLECTIONS -eq 0 ]; then
    echo "⚠️ No recent data collection activity"
fi
```

## 📚 Best Practices

1. **Regular Monitoring**: Check logs daily for errors and performance issues
2. **Log Rotation**: Ensure automatic rotation is working to prevent disk space issues
3. **Error Investigation**: Always investigate ERROR level logs immediately
4. **Performance Tracking**: Monitor API response times for degradation
5. **Disk Space**: Keep an eye on log directory sizes
6. **Archive Management**: Regularly clean up old compressed logs if needed

## 🆘 Emergency Procedures

### High Disk Usage
```bash
# Emergency log cleanup
find backend/logs/ logs/ -name "*.log" -mtime +7 -exec gzip {} \;
find backend/logs/ logs/ -name "*.log.gz" -mtime +30 -delete
```

### System Not Collecting Data
```bash
# Quick diagnostic
./scripts/view_logs.sh --errors
./scripts/view_logs.sh --tail 50 collectors
```

### Complete Log Reset
```bash
# CAUTION: This removes all logs
rm -rf logs/* backend/logs/*
mkdir -p logs/archive backend/logs
./start_workers.sh
```

---

For additional support or questions about the logging system, refer to the main project documentation or check the error logs for specific troubleshooting guidance.