# Social Media Cursor Tracking

This document describes the implementation of cursor tracking and deduplication for social media content fetching to prevent fetching the same items repeatedly from RapidAPI.

## Overview

The social media cursor tracking system ensures that:
- **No duplicate content** is fetched from social media platforms
- **Cursor-based pagination** is properly managed for each platform
- **Sync state** is tracked and persisted for each social account
- **Content deduplication** prevents storing the same posts multiple times

## Database Schema

### New Tables

#### `social_sync_states`
Tracks sync state and cursors for social media accounts:

```sql
CREATE TABLE social_sync_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    sync_type VARCHAR(50) NOT NULL, -- 'posts', 'comments', 'reactions', etc.
    last_cursor TEXT, -- Platform-specific cursor for pagination
    last_sync_timestamp TIMESTAMP WITH TIME ZONE,
    last_item_id VARCHAR(255), -- ID of the last item synced
    sync_config JSONB DEFAULT '{}', -- Platform-specific sync configuration
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'paused', 'error'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(social_account_id, sync_type)
);
```

#### `social_media_content`
Stores fetched social media content with deduplication:

```sql
CREATE TABLE social_media_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    content_type VARCHAR(50) NOT NULL, -- 'post', 'comment', 'reaction'
    platform_content_id VARCHAR(255) NOT NULL, -- Original platform content ID
    content_data JSONB NOT NULL, -- Full content data from platform
    author_id VARCHAR(255),
    author_name VARCHAR(255),
    content_text TEXT,
    media_urls TEXT[],
    engagement_metrics JSONB, -- likes, shares, comments, etc.
    published_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE, -- Whether content has been processed for moderation/analysis
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, platform_content_id)
);
```

### Updated Tables

#### `social_accounts`
Added cursor tracking fields:

```sql
ALTER TABLE social_accounts 
ADD COLUMN last_cursor TEXT,
ADD COLUMN sync_config JSONB DEFAULT '{}',
ADD COLUMN last_sync_status VARCHAR(50) DEFAULT 'success',
ADD COLUMN sync_error_message TEXT;
```

## Implementation

### SocialFetchService

The `SocialFetchService` class provides the core functionality:

#### Key Methods

- `get_sync_state()` - Retrieve current sync state for an account
- `update_sync_state()` - Update sync state with new cursor and item ID
- `store_content()` - Store content with deduplication
- `fetch_facebook_posts()` - Fetch Facebook posts with cursor tracking
- `fetch_twitter_posts()` - Fetch Twitter posts with cursor tracking
- `get_unprocessed_content()` - Get unprocessed content for moderation

#### Cursor Tracking Flow

1. **Initial Fetch**: No cursor exists, fetch from beginning
2. **Subsequent Fetches**: Use stored cursor to continue from last position
3. **Deduplication**: Check if content already exists before storing
4. **State Update**: Update cursor and last item ID after successful fetch

### Platform-Specific Implementation

#### Facebook
- Uses `cursor` parameter in API requests
- Cursor is returned in response as `cursor` field
- Content ID is `post_id`

#### Twitter
- Uses `cursor` parameter in API requests
- Cursor is returned in response as `cursor.bottom` field
- Content ID is `rest_id` from nested result structure

## API Endpoints

### New Endpoints

#### `POST /social-accounts/{account_id}/fetch-content`
Fetch social media content with cursor tracking:

```bash
curl -X POST "http://localhost:8000/v1/social-accounts/{account_id}/fetch-content" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "news",
    "max_items": 20
  }'
```

#### `GET /social-accounts/{account_id}/sync-state`
Get current sync state for an account:

```bash
curl -X GET "http://localhost:8000/v1/social-accounts/{account_id}/sync-state?sync_type=posts" \
  -H "Authorization: Bearer {token}"
```

#### `GET /social-accounts/content/unprocessed`
Get unprocessed content for moderation:

```bash
curl -X GET "http://localhost:8000/v1/social-accounts/content/unprocessed?platform=facebook&limit=50" \
  -H "Authorization: Bearer {token}"
```

#### `POST /social-accounts/content/mark-processed`
Mark content as processed:

```bash
curl -X POST "http://localhost:8000/v1/social-accounts/content/mark-processed" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "content_ids": ["uuid1", "uuid2"]
  }'
```

#### `POST /social-accounts/{account_id}/reset-sync`
Reset sync state (removes cursor tracking):

```bash
curl -X POST "http://localhost:8000/v1/social-accounts/{account_id}/reset-sync?sync_type=posts" \
  -H "Authorization: Bearer {token}"
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# RapidAPI Configuration
RAPIDAPI_KEY=your_rapidapi_key_here
```

### Settings

The `Settings` class in `core/config.py` includes:

```python
# RapidAPI Configuration
rapidapi_key: Optional[str] = None
```

## Usage Examples

### Basic Content Fetching

```python
from services.social_fetch_service import SocialFetchService

# Initialize service
social_fetch_service = SocialFetchService(db_client)

# Fetch content with cursor tracking
success, posts = await social_fetch_service.fetch_social_content(
    social_account_id="account-uuid",
    platform="facebook",
    query="news",
    max_items=20
)

if success:
    print(f"Fetched {len(posts)} posts")
else:
    print("Failed to fetch content")
```

### Getting Unprocessed Content

```python
# Get unprocessed content for moderation
unprocessed = await social_fetch_service.get_unprocessed_content(
    tenant_id="tenant-uuid",
    platform="facebook",
    limit=50
)

for content in unprocessed:
    print(f"Content: {content['content_text'][:100]}...")
    
# Mark as processed
await social_fetch_service.mark_content_processed([content['id'] for content in unprocessed])
```

### Managing Sync State

```python
# Get current sync state
sync_state = await social_fetch_service.get_sync_state(account_id, "posts")
print(f"Last cursor: {sync_state.get('last_cursor')}")

# Reset sync state
await social_fetch_service.update_sync_state(
    account_id, "posts",
    last_cursor=None,
    last_item_id=None,
    status="reset"
)
```

## Testing

### Run the Test Script

```bash
python test_social_cursor.py
```

This will test:
- Cursor tracking and storage
- Content deduplication
- Sync state management
- Unprocessed content retrieval
- Sync state reset functionality

### Demo Job Integration

The demo job (`demo_job.py`) now includes social media fetching:

```python
# Step 1.5: Fetch social media content with cursor tracking
await self.fetch_social_media_content()
```

## Benefits

1. **Efficiency**: No duplicate API calls or content storage
2. **Reliability**: Cursor tracking ensures no content is missed
3. **Scalability**: Handles large volumes of social media content
4. **Flexibility**: Platform-agnostic design supports multiple social networks
5. **Monitoring**: Sync state provides visibility into fetch operations

## Troubleshooting

### Common Issues

1. **No content fetched**: Check if account is connected and has proper permissions
2. **Cursor errors**: Reset sync state to start fresh
3. **API rate limits**: Implement delays between requests
4. **Duplicate content**: Verify deduplication logic is working correctly

### Debugging

Enable debug logging to see detailed cursor tracking:

```python
import logging
logging.getLogger('services.social_fetch_service').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Additional Platforms**: Support for Instagram, LinkedIn, etc.
2. **Advanced Filtering**: Content filtering based on keywords, engagement, etc.
3. **Batch Processing**: Process multiple accounts in parallel
4. **Webhook Integration**: Real-time content updates via webhooks
5. **Analytics**: Track fetch performance and success rates
