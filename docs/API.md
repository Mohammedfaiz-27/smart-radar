# SMART RADAR API Documentation

## Overview

The SMART RADAR API provides endpoints for managing social media intelligence operations including keyword clusters, strategic narratives, post analysis, and AI-powered response generation.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication is required for the MVP. All endpoints are publicly accessible.

## Data Models

### Cluster
```json
{
  "id": "string",
  "name": "string",
  "cluster_type": "own" | "competitor",
  "keywords": ["string"],
  "thresholds": {
    "twitter": {
      "min_likes": 500,
      "min_shares": 50
    }
  },
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Narrative
```json
{
  "id": "string",
  "name": "string",
  "language": "English",
  "talking_points": ["string"],
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Social Post
```json
{
  "id": "string",
  "platform": "twitter" | "facebook" | "instagram" | "linkedin",
  "platform_post_id": "string",
  "cluster_id": "string",
  "cluster_type": "own" | "competitor",
  "author": {
    "username": "string",
    "display_name": "string",
    "profile_url": "string"
  },
  "content": {
    "text": "string",
    "media_urls": ["string"]
  },
  "engagement": {
    "likes": 0,
    "shares": 0,
    "comments": 0,
    "retweets": 0
  },
  "intelligence": {
    "sentiment_score": -0.85,
    "sentiment_label": "Negative",
    "is_threat": true,
    "threat_level": "high"
  },
  "post_url": "string",
  "posted_at": "2024-01-01T00:00:00Z",
  "collected_at": "2024-01-01T00:00:00Z",
  "has_been_responded_to": false
}
```

## API Endpoints

### Clusters

#### Get All Clusters
```http
GET /api/v1/clusters
```

Query Parameters:
- `cluster_type` (optional): Filter by "own" or "competitor"
- `is_active` (optional): Filter by active status
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Number of records to return (default: 100)

#### Create Cluster
```http
POST /api/v1/clusters
Content-Type: application/json

{
  "name": "Healthcare Opposition",
  "cluster_type": "competitor",
  "keywords": ["#HealthcareFail", "@opponent"],
  "thresholds": {
    "twitter": {
      "min_likes": 500
    }
  },
  "is_active": true
}
```

#### Get Cluster by ID
```http
GET /api/v1/clusters/{cluster_id}
```

#### Update Cluster
```http
PUT /api/v1/clusters/{cluster_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "is_active": false
}
```

#### Delete Cluster
```http
DELETE /api/v1/clusters/{cluster_id}
```

### Narratives

#### Get All Narratives
```http
GET /api/v1/narratives
```

Query Parameters:
- `language` (optional): Filter by language
- `is_active` (optional): Filter by active status
- `skip` (optional): Number of records to skip
- `limit` (optional): Number of records to return

#### Create Narrative
```http
POST /api/v1/narratives
Content-Type: application/json

{
  "name": "Healthcare Facts",
  "language": "English",
  "talking_points": [
    "Our plan covers 500,000+ people",
    "Opposition claims are fact-checked as false"
  ],
  "is_active": true
}
```

#### Get Narrative by ID
```http
GET /api/v1/narratives/{narrative_id}
```

#### Update Narrative
```http
PUT /api/v1/narratives/{narrative_id}
Content-Type: application/json

{
  "talking_points": [
    "Updated talking point"
  ]
}
```

#### Delete Narrative
```http
DELETE /api/v1/narratives/{narrative_id}
```

### Posts

#### Get Posts
```http
GET /api/v1/posts
```

Query Parameters:
- `cluster_type` (optional): "own" or "competitor"
- `cluster_id` (optional): Specific cluster ID
- `platform` (optional): Social media platform
- `is_threat` (optional): Filter by threat status
- `skip` (optional): Pagination offset
- `limit` (optional): Number of records

#### Get Threat Posts
```http
GET /api/v1/posts/threats
```

Query Parameters:
- `cluster_type` (optional): Filter by cluster type
- `sentiment_threshold` (optional): Minimum sentiment score (default: -0.5)

#### Get Post by ID
```http
GET /api/v1/posts/{post_id}
```

#### Mark Post as Responded
```http
PATCH /api/v1/posts/{post_id}/respond
```

### Responses

#### Generate AI Response
```http
POST /api/v1/responses/generate
Content-Type: application/json

{
  "original_post_id": "string",
  "narrative_id": "string",
  "user_id": "string"
}
```

Response:
```json
{
  "generated_text": "AI-generated response text",
  "original_post_id": "string",
  "narrative_id": "string"
}
```

#### Log Response Usage
```http
POST /api/v1/responses/log
Content-Type: application/json

{
  "original_post_id": "string",
  "narrative_id": "string",
  "generated_text": "string",
  "user_id": "string"
}
```

## WebSocket Events

### Connection
```javascript
const socket = io('ws://localhost:8000/ws');
```

### Events

#### New Post
```javascript
socket.on('message', (data) => {
  if (data.type === 'new_post') {
    // Handle new post data
    console.log(data.data); // Post object
  }
});
```

#### Alert
```javascript
socket.on('message', (data) => {
  if (data.type === 'alert') {
    // Handle threat alert
    console.log(data.data); // Alert object
  }
});
```

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `400`: Bad Request - Invalid input data
- `404`: Not Found - Resource doesn't exist
- `500`: Internal Server Error - Server-side error

## Rate Limiting

Currently no rate limiting is implemented for the MVP.

## Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "smart-radar-api"
}
```