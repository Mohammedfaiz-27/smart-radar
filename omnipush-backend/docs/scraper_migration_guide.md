# Social Media Scraper Migration Guide

## Overview

This guide explains the migration from the hardcoded `demo_job.py` to the new configurable social media scraper system.

## What Changed

### Before (demo_job.py)
- ❌ Hardcoded keywords and settings
- ❌ Single job with fixed schedule
- ❌ No per-tenant configuration
- ❌ No API management interface
- ❌ Limited error handling and recovery

### After (Configurable Scraper System)
- ✅ Multiple configurable jobs per tenant
- ✅ Flexible cron-based scheduling
- ✅ Rich settings and filters per job
- ✅ Full API management interface
- ✅ Comprehensive error handling and statistics
- ✅ Background runner with graceful shutdown

## Database Schema

Run the migration to add scraper tables:

```sql
-- Apply the scraper schema
psql -f schema/create_scraper_jobs.sql
```

Tables created:
- `scraper_jobs` - Job configurations with RLS policies
- `scraper_job_runs` - Execution history and statistics

## API Endpoints

New endpoints available at `/api/v1/scraper/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs` | List scraper jobs with stats |
| POST | `/jobs` | Create new scraper job |
| PUT | `/jobs/{id}` | Update scraper job |
| DELETE | `/jobs/{id}` | Delete scraper job |
| POST | `/jobs/{id}/run` | Manually trigger job |
| POST | `/jobs/{id}/enable` | Enable job |
| POST | `/jobs/{id}/disable` | Disable job |
| GET | `/jobs/{id}/runs` | Get job run history |
| GET | `/stats` | System statistics |

## Configuration Options

### Job Settings (`ScraperJobSettings`)

```python
{
    "max_posts_per_run": 10,           # Posts to process per run
    "auto_publish": false,             # Auto-publish approved posts
    "generate_news_card": true,        # Generate news cards
    "content_filters": ["tech", "AI"], # Content filters
    "min_engagement_threshold": 10,    # Minimum engagement
    "exclude_keywords": ["spam"],      # Keywords to exclude
    "language_filter": "en",           # Language filter
    "location_filter": "coimbatore",   # Location filter
    "date_range_days": 1               # Search date range
}
```

### Cron Scheduling Examples

```
"*/1 * * * *"   - Every minute
"*/5 * * * *"   - Every 5 minutes
"*/15 * * * *"  - Every 15 minutes
"0 * * * *"     - Every hour
"0 */6 * * *"   - Every 6 hours
"0 0 * * *"     - Daily at midnight
```

## Migration Steps

### 1. Database Setup

```bash
# Apply schema migration
psql -f schema/create_scraper_jobs.sql

# Install new dependencies
uv sync
# or
pip install croniter>=1.4.1
```

### 2. Create Sample Jobs

```bash
# Setup demo jobs (replaces demo_job.py functionality)
python demo_job_v2.py setup
```

### 3. Start Background Runner

```bash
# Option 1: Using demo script
python demo_job_v2.py run

# Option 2: Direct runner
python background/scraper_runner.py start

# Check status
python demo_job_v2.py status
```

### 4. API Usage Examples

#### Create a new scraper job:
```python
POST /api/v1/scraper/jobs
{
    "name": "Tech News Scraper",
    "description": "Scrape technology news",
    "keywords": ["technology", "AI", "blockchain"],
    "platforms": ["facebook", "twitter"],
    "schedule_cron": "*/5 * * * *",
    "is_enabled": true,
    "settings": {
        "max_posts_per_run": 5,
        "auto_publish": false,
        "generate_news_card": true,
        "content_filters": ["tech"],
        "language_filter": "en"
    }
}
```

#### List jobs with statistics:
```python
GET /api/v1/scraper/jobs?page=1&size=20&enabled_only=true
```

#### Get system statistics:
```python
GET /api/v1/scraper/stats
```

## Background Runner Features

### Process Management
- Graceful startup and shutdown
- Signal handling (SIGINT, SIGTERM)
- Concurrent job execution
- Error recovery and retry logic

### Monitoring
- Structured logging with timestamps
- Job execution statistics
- Error tracking and reporting
- Performance metrics

### Configuration
- Configurable check intervals
- Database connection management
- Resource cleanup on shutdown

## Key Differences from demo_job.py

### 1. Multi-tenancy
- Full tenant isolation with RLS policies
- Per-tenant job configuration
- Tenant-specific statistics and history

### 2. Flexibility
- Multiple jobs per tenant
- Different schedules per job
- Configurable keywords and platforms
- Rich filtering and settings

### 3. Reliability
- Database-backed job persistence
- Execution history and error tracking
- Graceful error handling
- Background service architecture

### 4. Management
- Full CRUD API for job management
- Enable/disable jobs without deletion
- Manual job execution triggers
- Comprehensive statistics

### 5. Scalability
- Concurrent job execution
- Efficient database queries
- Resource management
- Performance monitoring

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
   - Ensure database schema is applied

2. **Jobs not running**
   - Check if jobs are enabled: `GET /api/v1/scraper/jobs`
   - Verify next_run_at timestamps
   - Check background runner logs

3. **Permission errors**
   - Ensure RLS policies are applied
   - Verify tenant context in API calls
   - Check X-Tenant-ID headers

### Logs and Debugging

```bash
# Background runner logs
tail -f scraper_runner.log

# Check job execution history
GET /api/v1/scraper/jobs/{job_id}/runs

# System statistics
GET /api/v1/scraper/stats
```

## Migration Checklist

- [ ] Apply database schema (`create_scraper_jobs.sql`)
- [ ] Install dependencies (`croniter>=1.4.1`)
- [ ] Create sample jobs (`python demo_job_v2.py setup`)
- [ ] Start background runner
- [ ] Test API endpoints
- [ ] Verify job execution and statistics
- [ ] Update monitoring and alerting
- [ ] Retire old `demo_job.py` (keep for reference)

## Performance Considerations

### Resource Usage
- Each job runs in its own async task
- Database connections are shared
- Memory usage scales with concurrent jobs

### Optimization Tips
- Use appropriate cron schedules (avoid over-scheduling)
- Set reasonable `max_posts_per_run` limits
- Monitor success rates and adjust settings
- Use content filters to reduce processing overhead

### Monitoring
- Track job success rates
- Monitor database performance
- Watch for memory/CPU usage patterns
- Set up alerts for failed jobs

## Benefits of Migration

1. **Operational Excellence**
   - Better monitoring and observability
   - Graceful error handling
   - Resource management

2. **Flexibility**
   - Multiple jobs with different configurations
   - Easy enable/disable without code changes
   - Runtime configuration updates

3. **Scalability**
   - Multi-tenant architecture
   - Concurrent job execution
   - Database-backed persistence

4. **Maintainability**
   - Clear separation of concerns
   - API-driven management
   - Structured logging and debugging

5. **User Experience**
   - Web UI management (future)
   - Real-time statistics
   - Historical tracking