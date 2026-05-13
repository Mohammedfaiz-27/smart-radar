# Social Media JSON Parsing

This document explains how to use the social media JSON parsing functionality in the OmniPush backend.

## Overview

The system can now parse social media data from Facebook and Twitter in JSON format and convert it into structured news articles that can be processed through the moderation and publishing pipeline.

## Supported Data Formats

### Facebook Posts
The system expects Facebook posts in the following structure:

```json
{
  "city": "Coimbatore",
  "facebook_posts": {
    "results": [
      {
        "post_id": "6508865145803770",
        "type": "post",
        "url": "https://www.facebook.com/...",
        "message": "Post content here...",
        "timestamp": 1667301725,
        "author": {
          "id": "100064445419638",
          "name": "Kumudam - குமுதம்",
          "url": "https://www.facebook.com/KumudamOnline"
        },
        "image": null,
        "video": "https://www.facebook.com/...",
        "video_thumbnail": "https://scontent-fra3-2.xx.fbcdn.net/..."
      }
    ]
  }
}
```

### Twitter Posts
The system expects Twitter posts in the following structure:

```json
{
  "twitter_posts": {
    "result": {
      "timeline": {
        "instructions": [
          {
            "type": "TimelineAddEntries",
            "entries": [
              {
                "entryId": "tweet-1957708742704918945",
                "content": {
                  "itemContent": {
                    "tweet_results": {
                      "result": {
                        "legacy": {
                          "full_text": "Tweet content here...",
                          "created_at": "Tue Aug 19 07:38:31 +0000 2025",
                          "id_str": "1957708742704918945"
                        },
                        "core": {
                          "user_results": {
                            "result": {
                              "core": {
                                "screen_name": "username"
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            ]
          }
        ]
      }
    }
  }
}
```

## Usage

### 1. Direct Parsing (Programmatic)

```python
from services.news_service import NewsService

# Initialize the news service
news_service = NewsService()

# Parse JSON data
articles = news_service.parse_social_media_json(json_data, city="Coimbatore")

# Process articles
for article in articles:
    print(f"Title: {article.title}")
    print(f"Source: {article.source}")
    print(f"Content: {article.content}")
```

### 2. API Endpoint

Use the new API endpoint to parse and store social media data:

```bash
POST /api/v1/pipelines/{pipeline_id}/parse-social-media
```

**Request Body:**
```json
{
  "json_data": {
    "city": "Coimbatore",
    "facebook_posts": { ... },
    "twitter_posts": { ... }
  },
  "city": "Coimbatore"
}
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Article Title",
      "content": "Article content...",
      "source": "Facebook - Kumudam",
      "url": "https://facebook.com/...",
      "published_at": "2025-01-19T07:38:31+00:00",
      "category": "social_media",
      "relevance_score": 0.8,
      "moderation_status": "pending",
      "created_at": "2025-01-19T10:00:00+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 1
}
```

### 3. Complete Pipeline Integration

```python
# Parse social media data
articles = news_service.parse_social_media_json(json_data, city="Coimbatore")

# Store in database
stored_ids = await news_service.store_news_articles(articles, pipeline_id)

# Process through moderation
for article in articles:
    processed_news = await news_service.moderate_news_content(article)
    
    if processed_news.is_approved:
        # Generate social media post
        post_content = processed_news.post_content
        
        # Create post in the system
        post_data = {
            'title': f"Auto-generated: {article.title[:50]}...",
            'content': {'text': post_content},
            'status': 'draft',
            'metadata': {
                'source': 'automated_news',
                'original_article_url': article.url,
                'news_source': article.source
            }
        }
```

## Features

### Automatic Parsing
- Extracts post content, author information, and metadata
- Converts timestamps to proper datetime objects
- Handles both Facebook and Twitter data structures
- Creates meaningful titles from post content

### Content Processing
- Converts social media posts into structured news articles
- Maintains source attribution and URLs
- Preserves media attachments (images, videos)
- Calculates relevance scores

### Integration
- Seamlessly integrates with existing moderation pipeline
- Supports AI-powered content moderation
- Generates social media-ready post content
- Stores data in the existing news_items table

## Example Scripts

### Basic Parsing Test
Run `test_news_parsing.py` to test the parsing functionality with sample data.

### Complete Example
Run `example_social_media_parsing.py` for a comprehensive demonstration including:
- JSON data loading
- Article parsing
- Moderation testing
- Post generation

## Error Handling

The parsing function includes comprehensive error handling:
- Graceful handling of missing or malformed data
- Logging of parsing errors
- Fallback values for missing fields
- Validation of required fields

## Configuration

The parsing behavior can be customized through:
- City parameter for location-specific processing
- Relevance score calculation
- Category assignment
- Source formatting

## Next Steps

After parsing social media data:
1. Review parsed articles for accuracy
2. Process through moderation pipeline
3. Generate social media posts
4. Schedule for publication
5. Monitor engagement and performance
