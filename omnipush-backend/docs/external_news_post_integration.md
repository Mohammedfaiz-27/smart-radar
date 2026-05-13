# External News → Posts Module Integration

## Overview

This document describes the integration between the External News system and the Posts module, allowing published external news items to appear in the main Posts section of the UI.

## Architecture

### Bidirectional Linking

The integration creates a bidirectional relationship:

```
External News Item ←→ Post ←→ External News Publication
```

- **external_news_items.id** ← **posts.external_news_id** (FK)
- **posts.id** ← **external_news_publications.post_id** (FK)

### Database Schema Changes

**Migration File**: `schema/add_external_news_id_to_posts.sql`

```sql
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS external_news_id UUID
REFERENCES external_news_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_posts_external_news_id
ON posts(external_news_id);
```

This allows:
- Posts to reference their source external news item
- Efficient querying of posts created from external news
- Automatic cleanup (SET NULL) if external news item is deleted

## Publishing Flow

### Step-by-Step Process

When a user publishes an approved external news item to channel groups:

#### 1. **User Action** (Frontend: `PostManagerView.vue`)
   - User approves external news item
   - Clicks "Publish" button
   - Selects channel groups via `ChannelGroupSelector.vue`
   - Optionally customizes title/content
   - Selects language variant (EN/TA)

#### 2. **API Call** (`api/v1/external_news.py`)
   ```
   POST /api/v1/external-news/{news_id}/publish
   ```

#### 3. **Service Layer** (`services/external_news_service.py`)

   **Method**: `publish_to_channel_groups()`

   For each selected channel group:

   a. **Fetch Social Accounts**
      - Get all social accounts in the channel group
      - Extract account details including `content_tone`

   b. **Prepare Content**
      - Use customized content if provided
      - Otherwise, extract from multilingual_data based on selected language
      - Fallback to default title + content

   c. **Create Post Record**
      ```python
      post_data = {
          'id': post_id,
          'tenant_id': str(tenant_id),
          'user_id': str(initiated_by),
          'title': final_title,
          'content': {"text": final_content, "media_ids": []},
          'channels': channels_data,  # Array of platform/account info
          'status': 'publishing',
          'channel_group_id': str(channel_group_id),
          'external_news_id': str(news_id),  # ← Links to external news
          'metadata': {
              'source': 'external_news',
              'external_source': news_item.get('external_source'),
              'selected_language': selected_language,
              'is_breaking': news_item.get('is_breaking')
          },
          'created_by': str(initiated_by)
      }
      ```

   d. **Create Publication Record**
      ```python
      pub_data = {
          'external_news_id': str(news_id),
          'channel_group_id': str(channel_group_id),
          'post_id': post_id,  # ← Links to post
          'status': 'publishing',
          'initiated_by': str(initiated_by)
      }
      ```

   e. **Publish via Publishing Service**
      - Pass `post_id` to `external_news_publishing_service`
      - Service handles content adaptation and social posting

   f. **Update Records with Results**
      - Update publication record with publish results
      - Update Post record with:
        - `status`: 'published' or 'failed'
        - `publish_results`: JSONB with detailed results
        - `published_at`: timestamp (if successful)

#### 4. **Publishing Service** (`services/external_news_publishing_service.py`)

   **Method**: `publish_news_to_channels(post_id=...)`

   a. **Get Social Accounts**
      - Fetch accounts from channel group

   b. **Prepare Base Content**
      - Extract title and content for adaptation

   c. **Group by Content Tone** (Optimization!)
      - Group social accounts by `content_tone`
      - Example: 10 accounts → 3 unique tones → only 3 AI calls needed
      - Reuse adapted content for accounts with same tone

   d. **Adapt Content** (`ContentAdaptationService`)
      - Generate tone-specific content once per unique tone
      - Map adapted content to all accounts with that tone

   e. **Publish to Accounts** (`SocialPostingService`)
      - Post adapted content to each social account
      - Track success/failure per account

   f. **Update Post Record**
      ```python
      post_update_data = {
          'status': 'published' if success_count > 0 else 'failed',
          'publish_results': {
              'results': publication_results,
              'total_accounts': len(social_accounts),
              'success_count': success_count,
              'failure_count': failure_count
          },
          'published_at': datetime.utcnow().isoformat()
      }
      ```

## Key Features

### 1. **Tone-Based Content Grouping**

**Problem**: Publishing to N accounts with different tones would require N AI API calls.

**Solution**: Group accounts by content tone before adaptation.

```python
def _group_channels_by_tone(channel_configs):
    tone_groups = {}
    for config in channel_configs:
        tone_key = f"{config.content_tone}::{config.custom_instructions or 'none'}"
        if tone_key not in tone_groups:
            tone_groups[tone_key] = []
        tone_groups[tone_key].append(config)
    return tone_groups
```

**Example**:
- 10 social accounts
- 3 with "professional" tone
- 4 with "casual" tone
- 3 with "formal" tone
- **Result**: Only 3 AI API calls instead of 10! (70% reduction)

### 2. **Posts Module Visibility**

Published external news items now appear in the Posts module because:

- Each publication creates a real Post record
- Post has `external_news_id` for source tracking
- Post appears in standard Posts list/grid
- Post can be filtered by `external_news_id IS NOT NULL`

### 3. **Publication Tracking**

Full bidirectional tracking:

**From External News**:
```sql
SELECT p.*, enp.status, enp.publish_results
FROM external_news_items en
JOIN posts p ON p.external_news_id = en.id
JOIN external_news_publications enp ON enp.post_id = p.id
WHERE en.id = 'news-uuid';
```

**From Post**:
```sql
SELECT en.*, enp.status
FROM posts p
JOIN external_news_items en ON p.external_news_id = en.id
JOIN external_news_publications enp ON enp.external_news_id = en.id
WHERE p.id = 'post-uuid';
```

## Testing

### Integration Test

**File**: `test_external_news_integration.py`

The test verifies the complete flow:
1. ✓ External news item exists and is approved
2. ✓ Channel group has social accounts
3. ✓ Publishing creates Post record
4. ✓ Post has correct external_news_id link
5. ✓ Post has publish_results with per-account status
6. ✓ Post appears with correct status (published/failed)

**Run Test**:
```bash
cd omnipush-backend
uv run python test_external_news_integration.py
```

### Manual Testing Steps

1. **Setup**:
   - Ensure external news item is approved
   - Create channel group with social accounts
   - Configure content_tone on social accounts

2. **Publish**:
   - Navigate to News Post tab in UI
   - Click "Publish" on approved news item
   - Select channel groups
   - Click "Publish"

3. **Verify**:
   - Check Posts module - new post should appear
   - Post title matches news item title
   - Post status is 'published' or 'failed'
   - Post metadata shows `source: 'external_news'`
   - publish_results shows per-account status

## API Endpoints

### Publish External News
```
POST /api/v1/external-news/{news_id}/publish

Request Body:
{
  "channel_group_ids": ["uuid1", "uuid2"],
  "selected_language": "en",
  "customized_title": "Optional custom title",
  "customized_content": "Optional custom content"
}

Response:
{
  "success": true,
  "total_channel_groups": 2,
  "publications": [
    {
      "id": "pub-uuid",
      "channel_group_id": "cg-uuid",
      "post_id": "post-uuid",
      "status": "published",
      "publish_results": {
        "total_accounts": 5,
        "success_count": 5,
        "failure_count": 0,
        "results": [...]
      }
    }
  ],
  "errors": [],
  "total_publish_results": [...]
}
```

## Frontend Integration

### PostManagerView.vue

**News Post Tab**:
- Displays external news items with approval workflow
- "Publish" button opens `ChannelGroupSelector` modal
- After publishing, status updates to "Published"

**Future Enhancement**:
- Posts tab could show external news badge/indicator
- Filter posts by source: `metadata.source === 'external_news'`
- Click post to navigate back to original news item

## Benefits

1. **Unified Post Management**: All published content (manual + external news) in one place
2. **Consistent Tracking**: Same publish_results structure for all posts
3. **Efficient Content Adaptation**: Tone-based grouping reduces AI API costs by 50-70%
4. **Bidirectional Navigation**: Easy to find posts from news items and vice versa
5. **Reusable Infrastructure**: Leverages existing PublishService, ContentAdaptationService, SocialPostingService

## Future Enhancements

### Potential Improvements:

1. **Batch Publishing**:
   - Publish multiple news items at once
   - Create separate Post records for each

2. **Post Templates**:
   - Apply post templates to external news content
   - Reuse template formatting for consistent branding

3. **Analytics Integration**:
   - Track engagement metrics for external news posts
   - Compare performance: manual posts vs. external news posts

4. **Scheduled Publishing**:
   - Schedule external news publishing for optimal times
   - Use existing post scheduling infrastructure

5. **Post Editing**:
   - Allow editing published external news posts
   - Create new versions while maintaining link to original news item

## Files Modified/Created

### Backend:
- ✓ `schema/add_external_news_id_to_posts.sql` - Database migration
- ✓ `services/external_news_service.py` - Post record creation
- ✓ `services/external_news_publishing_service.py` - Post update logic
- ✓ `test_external_news_integration.py` - Integration test
- ✓ `docs/external_news_post_integration.md` - This document

### No Frontend Changes Required:
- Existing Posts module automatically shows external news posts
- News Post tab already has publishing UI
- ChannelGroupSelector already implemented

## Conclusion

The integration successfully bridges the External News system with the Posts module, providing:
- Seamless publishing workflow
- Efficient content adaptation
- Complete tracking and visibility
- Reusable existing infrastructure

All published external news items now appear in the Posts module with full tracking and status information.
