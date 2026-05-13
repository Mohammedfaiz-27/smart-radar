# Publish Now API - Technical Documentation

## Overview

The `/publish-now` API endpoint provides immediate publishing functionality for posts to social media platforms through channel groups. This endpoint implements a sophisticated multi-step publishing pipeline that includes content adaptation, news card generation, and platform-specific publishing logic.

## API Endpoint Details

**Endpoint:** `POST /api/v1/posts/publish-now`  
**Location:** `api/v1/posts.py` (lines 723-863)  
**Authentication:** Required (JWT token)  
**Authorization:** Tenant-based access control

## Request/Response Models

### Request Model: `PublishNowRequest`
```python
class PublishNowRequest(BaseModel):
    post_id: str                    # Unique identifier for the post
    title: str                      # Post title
    content: str                    # Post content text
    channel_group_id: Optional[str] # Channel group ID for publishing
    image_url: Optional[str]        # Direct image URL to use
    media_ids: Optional[List[str]]  # List of media asset IDs
    mode: Optional[str]             # Post mode: "news_card", "text", "image"
```

### Response Model: `PublishNowResponse`
```python
class PublishNowResponse(BaseModel):
    success: bool                   # Overall publishing success status
    error: Optional[str]           # Error message if failed
    channels: Optional[dict]       # Publishing results per channel
    published_at: Optional[str]    # Timestamp of successful publishing
    news_card_url: Optional[str]   # Generated news card URL
```

## Step-by-Step Technical Flow

### Step 1: Request Validation and Authentication
**Location:** `api/v1/posts.py:724-728`

**Classes/Methods Involved:**
- `get_current_user()` - JWT token validation
- `get_tenant_context()` - Tenant context extraction
- `JWTPayload` - User authentication model
- `TenantContext` - Tenant isolation context

**Business Logic:**
- Validates JWT token and extracts user information
- Establishes tenant context for multi-tenancy
- Logs the publishing request with user and post details

### Step 2: Channel Group Resolution
**Location:** `api/v1/posts.py:735-760`

**Classes/Methods Involved:**
- `ChannelGroupsService.get_channel_group()`
- Database query: `ctx.table('social_accounts').select()`

**Business Logic:**
- Retrieves channel group configuration using `channel_group_id`
- Validates channel group exists for the tenant
- Fetches associated social accounts from the database
- Returns error if no social accounts are found

**Database Tables:**
- `channel_groups` - Channel group configurations
- `social_accounts` - Social media account details

### Step 3: Publish Service Initialization
**Location:** `api/v1/posts.py:762-780`

**Classes/Methods Involved:**
- `PublishConfig` - Publishing configuration
- `PublishService` - Main publishing orchestration service

**Configuration Parameters:**
```python
publish_config = PublishConfig(
    channels=[],                    # Determined by social accounts
    publish_text=True,             # Enable text publishing
    publish_image=True,            # Enable image publishing
    generate_news_card=True,       # Enable news card generation
    facebook_access_token=token,   # Facebook API credentials
    periskope_api_key=key,        # WhatsApp API credentials
    channel_group_id=group_id,    # Channel group reference
    social_accounts=accounts      # Social account details
)
```

**Environment Variables Used:**
- `FB_LONG_LIVED_TOKEN` / `FACEBOOK_ACCESS_TOKEN`
- `PERISKOPE_API_KEY`

### Step 4: Media Processing
**Location:** `api/v1/posts.py:782-810`

**Classes/Methods Involved:**
- Database queries for media assets
- Media URL construction logic

**Business Logic:**
- Processes `media_ids` to retrieve media file information
- Constructs media URLs in format: `/media/{tenant_id}/{file_name}`
- Falls back to `media_assets` table if `media` table not found
- Uses provided `image_url` or first media URL as primary image

**Database Tables:**
- `media` - Primary media storage table
- `media_assets` - Fallback media storage table

### Step 5: Post Mode Determination
**Location:** `api/v1/posts.py:812-830`

**Business Logic:**
- Analyzes content and media availability
- Determines post mode based on:
  - `has_text`: Boolean check for non-empty content
  - `has_media`: Boolean check for media presence
- Post mode mapping:
  - `text_with_images`: Has both text and media
  - `text`: Text-only content
  - `image`: Media-only content
  - `None`: Empty content and no media

### Step 6: Publish Service Execution
**Location:** `api/v1/posts.py:832-840`

**Classes/Methods Involved:**
- `PublishService.publish_post()` - Main publishing orchestration

**Parameters Passed:**
- `post_id`: Unique post identifier
- `title`: Post title
- `content`: Post content text
- `tenant_id`: Tenant context
- `user_id`: User who initiated publishing
- `image_url`: Primary image URL
- `post_mode`: Determined post mode

## PublishService Internal Flow

### Step 6.1: News Card Generation Decision
**Location:** `services/publish_service.py:120-160`

**Classes/Methods Involved:**
- `generate_news_card_from_text()` - News card generation service

**Business Logic:**
- Determines if news card generation is needed based on:
  - No provided image URL
  - News card generation enabled in config
  - Post mode requirements
- News card generation rules:
  - `news_card` mode: Always generate
  - `image` mode without image: Generate
  - `text` mode: Skip generation
  - `text_with_images` mode: Skip generation
  - No mode specified: Generate (backwards compatibility)

### Step 6.2: Post Status Update
**Location:** `services/publish_service.py:162-165`

**Classes/Methods Involved:**
- `_update_post_status()` - Database status update
- `PostStatus.PUBLISHING` - Status enumeration

**Database Operation:**
- Updates post status to `PUBLISHING`
- Records timestamp of publishing initiation

### Step 6.3: Publishing Target Determination
**Location:** `services/publish_service.py:167-175`

**Business Logic:**
- Routes to appropriate publishing method based on configuration:
  - Channel group accounts: `_publish_to_channel_group_accounts()`
  - Traditional channels: `_publish_to_configured_channels()`

## Channel Group Publishing Flow

### Step 6.3.1: Content Adaptation Setup
**Location:** `services/publish_service.py:280-310`

**Classes/Methods Involved:**
- `ContentAdaptationService.get_channel_configs()`
- `ChannelConfig` - Channel configuration model

**Business Logic:**
- Retrieves channel-specific configurations for content adaptation
- Falls back to default configurations if none found
- Creates `ChannelConfig` objects for each social account

### Step 6.3.2: Batch Content Adaptation
**Location:** `services/publish_service.py:312-325`

**Classes/Methods Involved:**
- `ContentAdaptationService.adapt_content_batch()`
- `BatchAdaptationResult` - Batch processing results

**Business Logic:**
- Processes up to 10 channels per batch for efficiency
- Uses OpenAI GPT-4 for content adaptation
- Adapts content based on channel-specific tone and style
- Tracks adaptation results in database

**AI Processing:**
- Model: `gpt-4o`
- Temperature: 0.7
- Max tokens: 400
- Batch size: 10 channels

### Step 6.3.3: Content Adaptation Mapping
**Location:** `services/publish_service.py:327-340`

**Business Logic:**
- Creates mapping of `channel_id` to adapted content
- Tracks adaptation results in database
- Handles adaptation failures gracefully

### Step 6.3.4: Per-Channel Publishing
**Location:** `services/publish_service.py:342-420`

**Classes/Methods Involved:**
- `_publish_to_facebook_account()`
- `_publish_to_whatsapp_account()`
- `_publish_to_instagram_account()`
- `_publish_to_twitter_account()`

**Business Logic:**
- Iterates through each social account
- Uses adapted content or falls back to original
- Generates channel-specific news cards if needed
- Publishes to platform-specific APIs

## Platform-Specific Publishing

### Facebook Publishing
**Location:** `services/publish_service.py:540-620`

**Classes/Methods Involved:**
- `FacebookSimpleClient` - Facebook API client
- `get_page_details_by_id()` - Page information retrieval
- `post_images_then_feed()` - Image and text posting

**Business Logic:**
- Validates Facebook access token
- Retrieves page details and access token
- Posts images first, then creates feed post
- Handles both image and text-only posts

**API Endpoints Used:**
- Facebook Graph API v22.0
- Page photos endpoint
- Page feed endpoint

### WhatsApp Publishing
**Location:** `services/publish_service.py:622-680`

**Classes/Methods Involved:**
- `post_to_whatsapp_group()` - WhatsApp API integration

**Business Logic:**
- Validates Periskope API key
- Retrieves WhatsApp group ID from account
- Posts message and optional media
- Supports images and videos

**API Endpoints Used:**
- Periskope API v1
- Message send endpoint

### Instagram Publishing
**Location:** `services/publish_service.py:682-720`

**Business Logic:**
- Similar to Facebook (Instagram uses Facebook Graph API)
- Handles Instagram-specific content requirements
- Supports image and video content

### Twitter Publishing
**Location:** `services/publish_service.py:722-760`

**Business Logic:**
- Twitter API v2 integration
- Handles character limits and media uploads
- Supports text and media content

## Content Adaptation Service

### Batch Processing
**Location:** `services/content_adaptation_service.py:70-130`

**Classes/Methods Involved:**
- `adapt_content_batch()` - Main batch processing
- `_process_batch()` - Individual batch processing

**Business Logic:**
- Groups channels into batches of 10
- Uses OpenAI for content adaptation
- Handles empty content gracefully
- Implements rate limiting between batches

### AI-Powered Adaptation
**Location:** `services/content_adaptation_service.py:135-200`

**Business Logic:**
- Constructs adaptation prompts for each channel
- Uses channel-specific tone and style instructions
- Generates hashtags and adapted content
- Handles API failures gracefully

## News Card Generation

### Content Service Integration
**Location:** `services/content_service.py:660-825`

**Classes/Methods Involved:**
- `generate_news_card_from_text()` - News card generation
- `generate_html_content()` - HTML content generation
- `generate_screenshot()` - Screenshot capture

**Business Logic:**
- Adapts content for news card format (max 180 characters)
- Generates HTML using LLM or template fallback
- Captures screenshot of generated HTML
- Stores news card in static directory

## Error Handling and Fallbacks

### Graceful Degradation
**Location:** Throughout the publishing flow

**Business Logic:**
- Falls back to original content if adaptation fails
- Continues publishing to other channels if one fails
- Uses template-based generation if AI fails
- Provides detailed error messages for debugging

### Status Tracking
**Location:** `services/publish_service.py:200-230`

**Business Logic:**
- Updates post status based on publishing results
- Tracks individual channel results
- Stores metadata with publishing details
- Handles partial success scenarios

## Database Operations

### Tables Involved
1. **posts** - Post storage and status tracking
2. **channel_groups** - Channel group configurations
3. **social_accounts** - Social media account details
4. **media** - Media asset storage
5. **media_assets** - Alternative media storage
6. **content_adaptations** - Content adaptation tracking

### Key Operations
- Post status updates
- Social account retrieval
- Media asset lookup
- Adaptation result tracking
- Publishing metadata storage

## Performance Considerations

### Optimization Strategies
1. **Batch Processing**: Content adaptation in batches of 10
2. **Caching**: Facebook client caching per tenant
3. **Rate Limiting**: Delays between API calls
4. **Parallel Processing**: Independent channel publishing
5. **Fallback Mechanisms**: Multiple content generation strategies

### Resource Usage
- OpenAI API calls for content adaptation
- Facebook Graph API calls for posting
- Periskope API calls for WhatsApp
- Screenshot generation for news cards
- Database operations for status tracking

## Security Considerations

### Authentication & Authorization
- JWT token validation
- Tenant-based access control
- User permission verification
- API key management

### Data Protection
- Tenant isolation
- Secure token storage
- API key encryption
- Access logging

## Monitoring and Logging

### Logging Points
- Request initiation
- Channel group resolution
- Content adaptation results
- Publishing attempts and results
- Error conditions and fallbacks

### Metrics to Track
- Publishing success rates
- Content adaptation performance
- API response times
- Error frequencies by platform
- News card generation success

## Troubleshooting Guide

### Common Issues
1. **No Social Accounts**: Check channel group configuration
2. **Content Adaptation Failures**: Verify OpenAI API key and quota
3. **Facebook Publishing Errors**: Validate access tokens and page permissions
4. **WhatsApp Publishing Errors**: Check Periskope API key and group ID
5. **News Card Generation Failures**: Verify screenshot service configuration

### Debug Steps
1. Check application logs for detailed error messages
2. Verify API credentials and permissions
3. Test individual platform publishing
4. Validate content adaptation settings
5. Review database connectivity and permissions

## Future Enhancements

### Planned Features
1. **Additional Platforms**: LinkedIn, TikTok, YouTube
2. **Advanced Analytics**: Publishing performance metrics
3. **A/B Testing**: Content variation testing
4. **Scheduling**: Advanced scheduling capabilities
5. **Automation**: Rule-based automatic publishing

### Technical Improvements
1. **Async Optimization**: Improved concurrency handling
2. **Caching Strategy**: Enhanced caching mechanisms
3. **Error Recovery**: Automatic retry mechanisms
4. **Monitoring**: Enhanced observability
5. **Testing**: Comprehensive test coverage
