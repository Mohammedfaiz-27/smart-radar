# API Examples

This document provides practical examples of using the OmniChannel Content Orchestrator API.

## Authentication Examples

### Sign Up (Create Tenant)
```bash
curl -X POST "http://localhost:8000/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "tenant_name": "Acme Marketing Agency",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Sign In
```bash
curl -X POST "http://localhost:8000/v1/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123"
  }'
```

## User Management Examples

### List Users
```bash
curl -X GET "http://localhost:8000/v1/users?page=1&limit=10" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

### Invite User
```bash
curl -X POST "http://localhost:8000/v1/users/invite" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "creator@example.com",
    "role": "creator",
    "first_name": "Jane",
    "last_name": "Smith"
  }'
```

## Content Management Examples

### Create Post
```bash
curl -X POST "http://localhost:8000/v1/posts" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summer Product Launch",
    "content": {
      "text": "🌟 Exciting news! Our new summer collection is here. Check it out and let us know what you think! #SummerLaunch #NewProducts",
      "media_ids": ["media_uuid_1", "media_uuid_2"]
    },
    "channels": [
      {
        "platform": "facebook",
        "account_id": "fb_account_uuid",
        "customizations": {
          "text": "🌟 Exciting news! Our new summer collection is here. Perfect for those sunny days ahead! Check it out and let us know what you think! #SummerLaunch #NewProducts #SummerVibes"
        }
      },
      {
        "platform": "twitter",
        "account_id": "twitter_account_uuid", 
        "customizations": {
          "text": "🌟 New summer collection is live! Check it out ☀️ #SummerLaunch #NewProducts"
        }
      },
      {
        "platform": "instagram",
        "account_id": "ig_account_uuid",
        "customizations": {
          "text": "🌟 Exciting news! Our new summer collection is here ☀️\n\nSwipe to see our favorite pieces from the collection. What\''s your favorite? Let us know in the comments! 👇\n\n#SummerLaunch #NewProducts #SummerVibes #Fashion #Style #OOTD"
        }
      }
    ],
    "scheduled_at": "2024-07-15T10:00:00Z"
  }'
```

### Update Post
```bash
curl -X PUT "http://localhost:8000/v1/posts/<post_id>" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated: Summer Product Launch",
    "content": {
      "text": "🌟 UPDATED: Our amazing new summer collection is here! Don\''t miss out - limited quantities available!"
    }
  }'
```

### List Posts with Filtering
```bash
# Get drafts only
curl -X GET "http://localhost:8000/v1/posts?status=draft&page=1&limit=10" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"

# Get posts by specific creator
curl -X GET "http://localhost:8000/v1/posts?created_by=<user_id>&page=1&limit=10" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Media Management Examples

### Upload Media
```bash
curl -X POST "http://localhost:8000/v1/media/upload" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -F "file=@/path/to/image.jpg" \
  -F "tags=[\"product\", \"summer\", \"campaign\"]" \
  -F "description=Summer product showcase image"
```

### Generate AI Image
```bash
curl -X POST "http://localhost:8000/v1/media/generate-ai" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Modern office workspace with plants and natural lighting",
    "style": "photographic",
    "size": "1024x1024"
  }'
```

### List Media with Search
```bash
curl -X GET "http://localhost:8000/v1/media?search=summer&type=image&page=1&limit=20" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Social Accounts Examples

### Connect Facebook Account
```bash
curl -X POST "http://localhost:8000/v1/social-accounts/connect" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "facebook",
    "auth_code": "facebook_oauth_code_from_frontend"
  }'
```

### List Connected Accounts
```bash
curl -X GET "http://localhost:8000/v1/social-accounts" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Scheduling & Publishing Examples

### Get Calendar View
```bash
curl -X GET "http://localhost:8000/v1/calendar?start_date=2024-07-01&end_date=2024-07-31&view=month" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

### Publish Post Now
```bash
curl -X POST "http://localhost:8000/v1/calendar/posts/<post_id>/publish" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": ["facebook", "twitter"]
  }'
```

### Bulk Schedule from CSV
```bash
curl -X POST "http://localhost:8000/v1/calendar/posts/bulk-schedule" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -F "csv_file=@bulk_posts.csv"
```

Example CSV content:
```csv
title,content,platform,account_id,scheduled_at,media_urls
"Morning Motivation","Start your day right! ☀️","facebook","fb_account_uuid","2024-07-15T08:00:00Z","https://example.com/image1.jpg"
"Afternoon Update","Hope everyone is having a great day! 😊","twitter","twitter_account_uuid","2024-07-15T14:00:00Z",""
"Evening Wrap-up","What a fantastic day! Thank you all for your support 🙏","instagram","ig_account_uuid","2024-07-15T18:00:00Z","https://example.com/image2.jpg,https://example.com/image3.jpg"
```

## Analytics Examples

### Get Post Analytics
```bash
curl -X GET "http://localhost:8000/v1/analytics/posts/<post_id>" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

### Get Dashboard Analytics
```bash
curl -X GET "http://localhost:8000/v1/analytics/dashboard?date_range=last_30_days" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

### Export Analytics Data
```bash
curl -X GET "http://localhost:8000/v1/analytics/export?date_range=last_30_days&format=csv" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -o analytics_export.csv
```

### Get Insights
```bash
curl -X GET "http://localhost:8000/v1/analytics/insights" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## AI Assistant Examples

### Generate Content Suggestions
```bash
curl -X POST "http://localhost:8000/v1/ai/content-suggestions" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "New product launch for eco-friendly water bottles",
    "platform": "instagram",
    "tone": "enthusiastic",
    "max_length": 280
  }'
```

### Optimize Content for Platform
```bash
curl -X POST "http://localhost:8000/v1/ai/optimize-content" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Check out our amazing new product that will revolutionize your daily routine! This incredible innovation brings together cutting-edge technology and user-friendly design to create something truly special.",
    "source_platform": "facebook",
    "target_platform": "twitter"
  }'
```

### Get Content Ideas
```bash
curl -X POST "http://localhost:8000/v1/ai/content-ideas?topic=sustainable living&count=5" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Workflow Management Examples

### Create Workflow
```bash
curl -X POST "http://localhost:8000/v1/workflows" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High-Value Content Approval",
    "description": "Multi-stage approval for important campaigns",
    "steps": [
      {
        "order": 1,
        "type": "approval",
        "approvers": ["content_manager_uuid"],
        "required": true
      },
      {
        "order": 2, 
        "type": "approval",
        "approvers": ["brand_manager_uuid", "marketing_director_uuid"],
        "required": true
      }
    ]
  }'
```

### Set Default Workflow
```bash
curl -X POST "http://localhost:8000/v1/workflows/<workflow_id>/set-default" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Webhook Examples

### Register Webhook
```bash
curl -X POST "http://localhost:8000/v1/webhooks" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhooks/omnipush",
    "events": ["post.published", "post.failed", "approval.required"],
    "secret": "your_webhook_secret_key"
  }'
```

### Test Webhook
```bash
curl -X POST "http://localhost:8000/v1/webhooks/<webhook_id>/test" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

## Tenant Management Examples

### Get Tenant Details
```bash
curl -X GET "http://localhost:8000/v1/tenants/me" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>"
```

### Update Subscription
```bash
curl -X POST "http://localhost:8000/v1/tenants/me/subscription/change" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "pro"
  }'
```

## Error Handling

All API endpoints return errors in a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request payload is invalid",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "req_uuid"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error