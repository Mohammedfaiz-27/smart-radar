# Background Publishing Implementation

This document describes the implementation of background publishing for immediate post publishing with newscard generation and content adaptation.

## Overview

When a post is created for immediate publishing, the system now:
1. **Returns immediately** to the UI with a background task ID
2. **Processes newscard generation** in the background
3. **Adapts content** for each channel in the background
4. **Updates post status** throughout each stage
5. **Publishes to all channels** without blocking the UI

## Architecture

### Components

1. **BackgroundTaskService** (`services/background_task_service.py`)
   - Manages background tasks using asyncio
   - Tracks task progress and status
   - Handles task cleanup and statistics

2. **Updated Posts API** (`api/v1/posts.py`)
   - `/publish-now` endpoint supports background processing
   - Status tracking endpoints for real-time updates
   - Background task management endpoints

3. **Database Schema** (`schema/add_background_task_support.sql`)
   - New fields in posts table for task tracking
   - Optional background_tasks table for persistent storage

## Usage

### Frontend Integration

#### 1. Immediate Publishing Request
```javascript
// Frontend sends publish request
const response = await fetch('/api/v1/posts/publish-now', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    post_id: 'post-123',
    title: 'My Post',
    content: 'Post content...',
    channel_group_id: 'marketing-channels',
    mode: 'newscard_with_image',
    background_processing: true  // Enable background processing
  })
});

// Immediate response
const result = await response.json();
// {
//   "success": true,
//   "background_task_id": "bg-task-abc123",
//   "processing_status": "processing",
//   "channels": null,
//   "published_at": null
// }

// UI can immediately show "Publishing..." status
```

#### 2. Status Polling
```javascript
// Poll for status updates
const pollStatus = async (taskId) => {
  const response = await fetch(`/api/v1/posts/background-tasks/${taskId}`);
  const status = await response.json();

  // Update UI based on status
  if (status.status === 'processing') {
    updateProgressUI(status.progress);
  } else if (status.status === 'completed') {
    showSuccessUI(status.result);
  } else if (status.status === 'failed') {
    showErrorUI(status.error);
  }

  // Continue polling if still processing
  if (status.status === 'processing') {
    setTimeout(() => pollStatus(taskId), 1000);
  }
};
```

#### 3. Post Status Tracking
```javascript
// Get current post status
const postStatus = await fetch(`/api/v1/posts/${postId}/status`);
const status = await postStatus.json();

// Status includes:
// - post_id
// - status (draft, publishing, published, failed)
// - published_at
// - news_card_url
// - processing_task_id
// - error_message
// - metadata
```

### API Endpoints

#### POST `/api/v1/posts/publish-now`
- **Purpose**: Immediately publish a post with background processing
- **Parameters**:
  - `background_processing: true` (default) for background mode
  - `background_processing: false` for synchronous mode
- **Response**: Immediate return with task ID

#### GET `/api/v1/posts/{post_id}/status`
- **Purpose**: Get current processing status of a post
- **Response**: Post status and background task progress

#### GET `/api/v1/posts/background-tasks/{task_id}`
- **Purpose**: Get detailed status of a specific background task
- **Response**: Task status, progress, result, and error information

#### GET `/api/v1/posts/background-tasks`
- **Purpose**: List all active background tasks for the tenant
- **Response**: List of tasks and statistics

## Implementation Details

### Background Task Flow

1. **Task Creation**
   ```python
   task_id = await background_service.create_and_publish_post_task(
       post_id=post_id,
       title=title,
       content=content,
       tenant_id=tenant_id,
       user_id=user_id,
       channel_group_id=channel_group_id,
       social_accounts=social_accounts
   )
   ```

2. **Status Updates**
   - `pending` → Task created, waiting to start
   - `processing` → Task is running
   - `completed` → Task finished successfully
   - `failed` → Task encountered an error

3. **Progress Tracking**
   ```python
   progress = {
       "status_updated": "publishing",
       "publish_service_initialized": True,
       "newscard_generation": "completed",
       "content_adaptation": "completed",
       "publishing_completed": True,
       "channels_processed": 3
   }
   ```

### Database Schema Changes

```sql
-- Add to posts table
ALTER TABLE posts
ADD COLUMN processing_task_id VARCHAR(255),
ADD COLUMN error_message TEXT,
ADD COLUMN metadata JSONB DEFAULT '{}';

-- Optional: Create background_tasks table for persistence
CREATE TABLE background_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    progress JSONB DEFAULT '{}'
);
```

## Benefits

### User Experience
- ⚡ **Immediate Response**: UI doesn't block waiting for publishing
- 📊 **Real-time Updates**: Users see progress as it happens
- 🎯 **Clear Status**: Always know what's happening with posts
- ✨ **Seamless Flow**: Publishing feels instant and smooth

### Technical Benefits
- 🔄 **Non-blocking**: API remains responsive during heavy processing
- 📈 **Scalable**: Can handle multiple simultaneous publishing requests
- 🛡️ **Reliable**: Failed tasks don't crash the system
- 📋 **Trackable**: Full audit trail of publishing operations

### Publishing Features
- 🖼️ **Newscard Generation**: Created in background without delay
- 🎨 **Content Adaptation**: Customized content per channel
- 📱 **Multi-platform**: Publish to multiple social channels
- 🔧 **Error Handling**: Graceful handling of partial failures

## Error Handling

### Task Failures
- Tasks that fail update post status to `failed`
- Error messages are stored and accessible via API
- UI can display appropriate error messages and recovery options

### Partial Successes
- Some channels may succeed while others fail
- Results include per-channel success/failure status
- UI can show nuanced status (e.g., "Published to 2 of 3 channels")

### Recovery
- Failed tasks leave clear audit trail
- Posts can be republished manually
- Error messages help with troubleshooting

## Testing

### Unit Tests
```bash
# Run background publishing tests
uv run python test_background_publishing.py

# Run UI integration demo
uv run python demo_ui_integration.py
```

### Integration Testing
- Test with real social media API keys
- Verify newscard generation and content adaptation
- Test error scenarios and recovery

## Migration Steps

1. **Apply Database Migration**
   ```bash
   # Apply the schema changes
   psql -f schema/add_background_task_support.sql
   ```

2. **Deploy Backend Changes**
   - Deploy updated `BackgroundTaskService`
   - Deploy updated posts API endpoints
   - Verify background processing is working

3. **Update Frontend**
   - Add background processing request flag
   - Implement status polling
   - Update UI to show real-time progress

4. **Test and Monitor**
   - Monitor background task statistics
   - Verify publishing success rates
   - Check user experience metrics

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: Required for content adaptation
- `FB_LONG_LIVED_TOKEN`: Required for Facebook publishing
- `PERISKOPE_API_KEY`: Required for WhatsApp publishing

### Feature Flags
- `background_processing`: Enable/disable background processing
- Can be set per request or globally

## Monitoring

### Task Statistics
```python
# Get current task statistics
stats = background_service.get_task_statistics()
# Returns:
# {
#   "total_tasks": 150,
#   "running_tasks": 5,
#   "status_breakdown": {"completed": 140, "failed": 5, "processing": 5},
#   "task_types": ["publish_post"]
# }
```

### Performance Metrics
- Task completion times
- Success/failure rates
- Channel-specific performance
- User experience metrics

## Future Enhancements

### Persistence
- Move from in-memory task storage to database
- Enable task recovery after server restarts
- Historical task analysis

### Scaling
- Distribute tasks across multiple workers
- Queue-based task management (Redis/Celery)
- Load balancing for high-volume publishing

### Features
- Scheduled background publishing
- Batch publishing operations
- Advanced progress notifications
- WebSocket real-time updates instead of polling

## Conclusion

The background publishing implementation provides a significant improvement to user experience while maintaining all existing functionality. Users can now publish posts immediately without waiting for newscard generation and content adaptation, while still getting all the benefits of these features running in the background.

The system is designed to be:
- **Reliable**: Proper error handling and status tracking
- **Scalable**: Can handle concurrent publishing requests
- **User-friendly**: Immediate response with real-time updates
- **Maintainable**: Clean separation of concerns and good monitoring