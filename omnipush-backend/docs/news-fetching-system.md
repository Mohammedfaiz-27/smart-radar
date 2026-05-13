# News Fetching and Storage System

## Overview

The news fetching and storage system allows you to automatically fetch news from the local `/get-live-news` endpoint, store them in the database, and only fetch new news since the last sync. This system is designed to work with the existing pipeline and moderation infrastructure.

## Features

- **Local News Fetching**: Fetches news from the local `/get-live-news` endpoint
- **Incremental Sync**: Only fetches and stores new news since the last sync
- **Database Storage**: Stores news articles in the `news_items` table
- **Moderation Integration**: Integrates with the existing moderation system
- **API Endpoints**: Provides REST API endpoints for news management
- **Pipeline Support**: Works with the existing pipeline system

## Architecture

### Components

1. **NewsService** (`services/news_service.py`): Core service for news operations
2. **API Endpoints** (`api/v1/automation.py`): REST API for news management
3. **Database Schema** (`schema/supabase_schema_no_rls.sql`): News items table
4. **Local Endpoint** (`app.py`): `/get-live-news` endpoint

### Data Flow

1. **Fetch**: NewsService fetches data from `/get-live-news` endpoint
2. **Filter**: Filters out articles already processed since last sync
3. **Store**: Stores new articles in `news_items` table
4. **Process**: Integrates with moderation and content generation pipeline

## API Endpoints

### Fetch and Store News

```http
POST /api/v1/automation/fetch-news
```

**Request Body:**
```json
{
  "city": "Coimbatore",
  "pipeline_id": "optional-pipeline-id"
}
```

**Response:**
```json
{
  "success": true,
  "articles_fetched": 5,
  "articles_stored": 3,
  "last_sync": "2024-01-01T10:00:00Z",
  "new_sync_time": "2024-01-01T12:00:00Z"
}
```

### Get News Items

```http
GET /api/v1/automation/news-items/{pipeline_id}?limit=10
```

**Response:**
```json
[
  {
    "id": "uuid",
    "pipeline_id": "pipeline-uuid",
    "title": "News Title",
    "content": "News content...",
    "source": "Facebook",
    "source_url": "https://...",
    "published_at": "2024-01-01T10:00:00Z",
    "fetched_at": "2024-01-01T12:00:00Z",
    "moderation_status": "pending",
    "moderation_score": 0.8
  }
]
```

## Database Schema

### news_items Table

```sql
CREATE TABLE news_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    published_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    moderation_status moderation_status DEFAULT 'pending',
    moderation_score DECIMAL(3,2),
    moderation_flags TEXT[],
    processed_content TEXT,
    generated_image_url VARCHAR(500),
    published_channels TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Usage Examples

### Python Service Usage

```python
from services.news_service import NewsService

# Initialize service
news_service = NewsService()

# Fetch and store new news
result = await news_service.fetch_and_store_new_news(
    city="Coimbatore",
    pipeline_id="your-pipeline-id"
)

# Get pending articles
pending = await news_service.get_pending_news_articles(
    pipeline_id="your-pipeline-id",
    limit=10
)

# Process news batch
processed = await news_service.process_news_batch(
    city="Coimbatore",
    pipeline_id="your-pipeline-id",
    max_articles=5
)
```

### Testing

Run the test script to verify functionality:

```bash
python test_news_fetch.py
```

This will test:
1. Local endpoint connectivity
2. News fetching from local endpoint
3. News storage in database
4. News processing and moderation

## Configuration

### Environment Variables

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `SUPABASE_SERVICE_KEY`: Supabase service key (for bypassing RLS)

### Local Endpoint Configuration

The local `/get-live-news` endpoint should return data in this format:

```json
{
  "city": "Coimbatore",
  "facebook_posts": [
    {
      "message": "Post content...",
      "created_time": "2024-01-01T10:00:00Z",
      "permalink_url": "https://...",
      "id": "unique-id"
    }
  ],
  "twitter_posts": [
    {
      "text": "Tweet content...",
      "created_at": "2024-01-01T10:00:00Z",
      "url": "https://...",
      "id": "unique-id"
    }
  ],
  "fetched_at": "2024-01-01T12:00:00Z"
}
```

## Integration with Existing Systems

### Pipeline Integration

The news system integrates with the existing pipeline system:

1. **Pipeline Creation**: Create a pipeline for news processing
2. **News Fetching**: Use the pipeline ID to organize news items
3. **Moderation**: News items go through the moderation pipeline
4. **Content Generation**: Approved news can be converted to social media posts

### Moderation Integration

News articles are automatically processed through the moderation system:

1. **Pending Status**: New articles start with "pending" moderation status
2. **Moderation Processing**: Articles are processed by the moderation service
3. **Status Updates**: Moderation results update the article status
4. **Content Processing**: Approved articles can be processed for social media

## Error Handling

The system includes comprehensive error handling:

- **Network Errors**: Graceful handling of endpoint failures
- **Database Errors**: Proper error logging and recovery
- **Validation Errors**: Input validation and error responses
- **Rate Limiting**: Built-in delays to avoid overwhelming services

## Monitoring and Logging

The system provides detailed logging:

- **Fetch Operations**: Logs news fetching attempts and results
- **Storage Operations**: Logs database operations
- **Error Logging**: Detailed error information for debugging
- **Performance Metrics**: Tracks processing times and success rates

## Future Enhancements

Potential improvements for the news system:

1. **Multiple Sources**: Support for additional news sources
2. **Content Deduplication**: Advanced duplicate detection
3. **Scheduling**: Automated news fetching schedules
4. **Analytics**: News performance and engagement metrics
5. **Content Enrichment**: AI-powered content enhancement
6. **Real-time Updates**: WebSocket-based real-time news updates
