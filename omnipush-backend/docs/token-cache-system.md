# Token Cache System

## Overview

The Token Cache System provides local caching of Facebook page access tokens to improve performance and reduce API calls. Tokens are stored in JSON format and automatically refreshed when expired.

## Features

- **Local JSON Caching**: Tokens stored in `cache/facebook_tokens_cache.json`
- **Automatic Expiry**: 24-hour cache expiry with automatic refresh
- **API Fallback**: Falls back to Facebook API when cache fails
- **Error Handling**: Graceful handling of cache and API failures
- **Cache Management**: Methods to clear cache and get cache status

## Architecture

### TokenCacheService

The main service class that handles all token caching operations:

```python
from services.token_cache_service import TokenCacheService

# Initialize with custom cache directory
token_cache = TokenCacheService(cache_dir="cache")

# Get page access token (cached or from API)
page_details = token_cache.get_page_access_token(page_id, user_access_token)
```

### Cache Structure

The cache file (`facebook_tokens_cache.json`) has the following structure:

```json
{
  "last_updated": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-02T12:00:00Z",
  "page_tokens": {
    "61579232464240": {
      "page_name": "Example Page Name",
      "page_id": "61579232464240",
      "page_access_token": "EAA..."
    }
  }
}
```

## Usage

### Basic Usage

```python
from services.token_cache_service import TokenCacheService

# Initialize service
token_cache = TokenCacheService()

# Get page access token
page_details = token_cache.get_page_access_token(
    page_id="61579232464240",
    user_access_token="your_user_access_token"
)

if page_details:
    print(f"Page: {page_details['page_name']}")
    print(f"Token: {page_details['page_access_token']}")
```

### Integration with PublishService

The `PublishService` automatically uses the token cache:

```python
from services.publish_service import PublishService, PublishConfig

# Initialize with configuration
config = PublishConfig(
    facebook_access_token="your_user_access_token",
    # ... other config
)

service = PublishService(config)

# Publishing will automatically use cached tokens
result = await service.publish_post(post_id, title, content)
```

### Cache Management

```python
# Get cache information
cache_info = token_cache.get_cache_info()
print(f"Cache status: {cache_info}")

# Clear cache
token_cache.clear_cache()
```

## Demo Job Integration

The demo job now includes:

1. **Token Cache Initialization**: Automatically initializes token cache
2. **Cache Status Logging**: Logs cache status on startup
3. **Coimbatore Content Search**: Searches for "coimbatore" content on Facebook and Twitter
4. **Automatic Publishing**: Publishes approved content to configured channels

### Demo Job Features

- **Coimbatore Search**: Uses RapidAPI to search for "coimbatore" content
- **Content Processing**: Moderates found content using GPT
- **Auto-Publishing**: Automatically publishes approved content
- **Token Caching**: Uses cached Facebook tokens with API fallback

## Configuration

### Environment Variables

```bash
# Facebook Access Token
FB_LONG_LIVED_TOKEN=your_facebook_long_lived_token
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token

# RapidAPI Keys
RAPIDAPI_KEY_FACEBOOK=your_rapidapi_facebook_key
RAPIDAPI_KEY_TWITTER=your_rapidapi_twitter_key
```

### Cache Configuration

```python
# Custom cache directory
token_cache = TokenCacheService(cache_dir="custom_cache")

# Cache expiry (default: 24 hours)
CACHE_EXPIRY_HOURS = 24
```

## Error Handling

The system handles various error scenarios:

1. **Cache File Missing**: Automatically creates new cache
2. **Cache Expired**: Refreshes from API
3. **API Failure**: Returns None and logs error
4. **Invalid Tokens**: Handles gracefully with error messages

## Testing

Run the test script to verify functionality:

```bash
python test_token_cache.py
```

## Security Considerations

- Tokens are stored in plain text in the cache file
- Cache file should be secured and not committed to version control
- Consider encrypting cached tokens in production
- Cache directory should have appropriate permissions

## Performance Benefits

- **Reduced API Calls**: Cached tokens eliminate repeated API requests
- **Faster Publishing**: No delay waiting for token retrieval
- **Better Reliability**: Fallback to API when cache fails
- **Reduced Rate Limiting**: Fewer API calls to Facebook

## Monitoring

Monitor cache performance with:

```python
cache_info = token_cache.get_cache_info()
print(f"Cache hit rate: {cache_info['cached_pages']} pages cached")
print(f"Cache expiry: {cache_info['expires_at']}")
```

## Troubleshooting

### Common Issues

1. **Cache Not Working**: Check file permissions and directory access
2. **Tokens Expired**: Clear cache to force refresh
3. **API Errors**: Verify Facebook access token validity
4. **Missing Pages**: Ensure page ID exists in Facebook account

### Debug Commands

```python
# Check cache status
print(token_cache.get_cache_info())

# Clear cache
token_cache.clear_cache()

# Test token retrieval
page_details = token_cache.get_page_access_token(page_id, user_token)
print(f"Token retrieved: {page_details is not None}")
```
