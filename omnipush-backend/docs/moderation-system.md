# OmniPush Content Moderation System

## Overview

The OmniPush Content Moderation System is an AI-powered content filtering solution that ensures high-quality, relevant content for the platform. It specifically focuses on **Coimbatore city content** and **generic news** while filtering out spam and harmful content.

## Key Features

### 🎯 Content Focus
- **Coimbatore City Content**: Local news, events, developments, and community updates
- **Generic News**: High-quality national/international news with broad relevance
- **Spam & Harmful Content Filtering**: Automatic detection and rejection

### 🤖 AI-Powered Moderation
- **OpenAI GPT-4 Integration**: Advanced content analysis and classification
- **Safety Checks**: OpenAI moderation API for harmful content detection
- **Fallback System**: Keyword-based moderation when AI is unavailable

### 📊 Comprehensive Analysis
- **Content Type Classification**: Coimbatore local, generic news, spam, harmful
- **Confidence Scoring**: Reliability assessment for each moderation decision
- **Detailed Reasoning**: Clear explanations for approval/rejection decisions

## How It Works

### 1. Safety Check
The system first checks content for harmful or inappropriate material using OpenAI's moderation API:
- Violence, hate speech, harassment
- Misinformation, fake news
- Inappropriate or offensive content

### 2. Relevance Analysis
Content is analyzed for relevance using GPT-4 with specific criteria:

#### ✅ Accepted Content

**Coimbatore City Content:**
- Local news, events, and developments in Coimbatore
- Business, technology, education, healthcare news from Coimbatore
- Cultural, social, and community news from Coimbatore
- Infrastructure, real estate, and economic developments in Coimbatore
- Local government, civic issues, and public services in Coimbatore
- Educational institutions, hospitals, and major organizations in Coimbatore

**Generic News:**
- Major national/international developments with broad impact
- Technology breakthroughs and innovations
- Scientific discoveries and research
- Business and economic news of significance
- Health and wellness updates
- Environmental and sustainability news
- Educational and career development news

#### ❌ Rejected Content

- Spam, clickbait, or low-quality content
- Harmful, misleading, or fake news
- Content completely unrelated to Coimbatore or general news
- Overly promotional or commercial content without news value
- Content that could cause harm or spread misinformation
- Gossip, celebrity news, or entertainment without broader significance

### 3. Fallback Moderation
When OpenAI is unavailable, the system uses keyword-based moderation:
- Coimbatore-related keywords detection
- Spam indicator identification
- Harmful content keyword filtering

## API Endpoints

### Single Content Moderation
```http
POST /api/v1/moderation/moderate
```

**Request:**
```json
{
  "title": "New IT Park Opens in Coimbatore",
  "content": "A major technology hub has been inaugurated...",
  "source": "Coimbatore Business Times",
  "category": "technology"
}
```

**Response:**
```json
{
  "is_approved": true,
  "reason": "Content is relevant to Coimbatore city",
  "content_type": "coimbatore_local",
  "confidence": 0.95,
  "flagged_categories": null,
  "suggested_actions": []
}
```

### Batch Moderation
```http
POST /api/v1/moderation/moderate/batch
```

### Health Check
```http
GET /api/v1/moderation/health
```

### System Information
```http
GET /api/v1/moderation/info
```

## Usage Examples

### Python Integration

```python
from services.moderation_service import ModerationService

# Initialize service
moderation_service = ModerationService()

# Moderate single content
result = await moderation_service.moderate_content(
    title="Coimbatore Startup Wins Award",
    content="A local startup has won...",
    source="Local News",
    category="business"
)

print(f"Approved: {result.is_approved}")
print(f"Type: {result.content_type}")
print(f"Reason: {result.reason}")
```

### Batch Processing

```python
# Moderate multiple articles
articles = [
    {
        'title': 'Article 1',
        'content': 'Content 1...',
        'source': 'Source 1',
        'category': 'technology'
    },
    # ... more articles
]

results = await moderation_service.batch_moderate(articles)
stats = moderation_service.get_moderation_stats(results)

print(f"Approval rate: {stats['approval_rate']:.1%}")
```

## Testing

Run the moderation test suite:

```bash
python test_moderation.py
```

This will test:
- ✅ Coimbatore-specific content approval
- ✅ Generic news content approval
- ❌ Spam and harmful content rejection
- 📊 Batch processing and statistics

## Configuration

### Environment Variables

```bash
# Required for AI-powered moderation
OPENAI_API_KEY=your_openai_api_key

# Optional: News API for content fetching
NEWS_API_KEY=your_news_api_key
```

### Fallback Behavior

When OpenAI is not configured:
- System falls back to keyword-based moderation
- Coimbatore keywords: `coimbatore`, `kovai`, `tamil nadu`, `psg`, etc.
- Spam indicators: `click here`, `buy now`, `limited time`, etc.
- Harmful indicators: `hate speech`, `violence`, `fake news`, etc.

## Integration with News Service

The moderation system is integrated with the news service:

```python
from services.news_service import NewsService

news_service = NewsService()

# Fetch and moderate news
articles = await news_service.fetch_latest_news(category="technology")
processed_news = []

for article in articles:
    processed = await news_service.moderate_news_content(article)
    processed_news.append(processed)
    
    if processed.is_approved:
        print(f"✅ Approved: {article.title}")
    else:
        print(f"❌ Rejected: {processed.moderation_reason}")
```

## Demo Job Integration

The demo job (`demo_job.py`) showcases the moderation system:

```bash
python demo_job.py
```

Features:
- Automated news fetching
- Content moderation with Coimbatore focus
- Post creation from approved content
- Scheduling for publishing

## Performance Considerations

- **Rate Limiting**: Built-in delays between API calls
- **Batch Processing**: Efficient handling of multiple articles
- **Caching**: Results can be cached for repeated content
- **Error Handling**: Graceful fallback when services are unavailable

## Monitoring and Analytics

The system provides comprehensive statistics:
- Approval/rejection rates
- Content type distribution
- Confidence scores
- Processing times
- Error rates

## Future Enhancements

- **Custom Keywords**: Tenant-specific keyword configuration
- **Learning System**: Improve accuracy based on user feedback
- **Multi-language Support**: Tamil language content analysis
- **Real-time Monitoring**: Live moderation dashboard
- **Advanced Filtering**: More sophisticated spam detection

## Support

For questions or issues with the moderation system:
- Check the health endpoint: `/api/v1/moderation/health`
- Review logs for detailed error information
- Test with the provided test suite
- Contact the development team for assistance
