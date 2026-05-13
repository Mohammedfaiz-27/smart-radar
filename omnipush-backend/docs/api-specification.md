# OmniChannel Content Orchestrator API Specification

## Overview

This document outlines the complete API specification for the OmniChannel Content Orchestrator, a multi-tenant SaaS platform built with Vue.js frontend and Supabase backend with Python wrapper for UI functionalities.

**Base URL**: `https://api.omnipush.com/v1`
**Authentication**: Bearer Token (JWT)
**Content-Type**: `application/json`

## Authentication & Security

### Headers
```
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
Content-Type: application/json
```

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid"
}
```

## 1. Authentication APIs

### 1.1 User Authentication

#### Sign Up
```http
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "tenant_name": "My Company",
  "first_name": "John",
  "last_name": "Doe"
}

Response: 201
{
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "tenant": {
    "id": "tenant_uuid",
    "name": "My Company",
    "subscription_tier": "basic"
  },
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "expires_in": 3600
}
```

#### Sign In
```http
POST /auth/signin
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}

Response: 200
{
  "user": {
    "id": "user_uuid",
    "email": "user@example.com",
    "tenant_id": "tenant_uuid",
    "role": "admin",
    "first_name": "John",
    "last_name": "Doe"
  },
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "expires_in": 3600
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token"
}

Response: 200
{
  "access_token": "new_jwt_token",
  "expires_in": 3600
}
```

#### Sign Out
```http
POST /auth/signout
Authorization: Bearer <jwt_token>

Response: 200
{
  "message": "Successfully signed out"
}
```

## 2. Tenant Management APIs

### 2.1 Tenant Operations

#### Get Tenant Details
```http
GET /tenants/me
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "id": "tenant_uuid",
  "name": "My Company",
  "subscription_tier": "pro",
  "subscription_status": "active",
  "billing_email": "billing@company.com",
  "created_at": "2024-01-01T00:00:00Z",
  "usage_limits": {
    "users": 10,
    "posts_per_month": 1000,
    "ai_generations_per_month": 100,
    "storage_gb": 50
  },
  "current_usage": {
    "users": 5,
    "posts_this_month": 250,
    "ai_generations_this_month": 25,
    "storage_used_gb": 12.5
  }
}
```

#### Update Tenant
```http
PUT /tenants/me
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "name": "Updated Company Name",
  "billing_email": "new-billing@company.com"
}

Response: 200
{
  "id": "tenant_uuid",
  "name": "Updated Company Name",
  "billing_email": "new-billing@company.com",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 2.2 Subscription Management

#### Get Subscription Details
```http
GET /tenants/me/subscription
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "tier": "pro",
  "status": "active",
  "current_period_start": "2024-01-01T00:00:00Z",
  "current_period_end": "2024-02-01T00:00:00Z",
  "stripe_customer_id": "cus_stripe_id",
  "stripe_subscription_id": "sub_stripe_id"
}
```

#### Update Subscription
```http
POST /tenants/me/subscription/change
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "tier": "enterprise"
}

Response: 200
{
  "tier": "enterprise",
  "status": "active",
  "change_effective_date": "2024-02-01T00:00:00Z"
}
```

#### Get Billing History
```http
GET /tenants/me/billing/invoices
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "invoices": [
    {
      "id": "inv_stripe_id",
      "amount": 2900,
      "currency": "usd",
      "status": "paid",
      "created": "2024-01-01T00:00:00Z",
      "invoice_pdf": "https://stripe.com/invoice.pdf"
    }
  ]
}
```

## 3. User Management APIs

### 3.1 User Operations

#### List Tenant Users
```http
GET /users
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
?page=1&limit=20&role=creator

Response: 200
{
  "users": [
    {
      "id": "user_uuid",
      "email": "user@company.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "role": "creator",
      "status": "active",
      "last_login": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### Invite User
```http
POST /users/invite
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "email": "newuser@company.com",
  "role": "creator",
  "first_name": "New",
  "last_name": "User"
}

Response: 201
{
  "invitation": {
    "id": "invitation_uuid",
    "email": "newuser@company.com",
    "role": "creator",
    "status": "pending",
    "expires_at": "2024-01-08T00:00:00Z"
  }
}
```

#### Update User Role
```http
PUT /users/{user_id}/role
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "role": "editor"
}

Response: 200
{
  "id": "user_uuid",
  "role": "editor",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Deactivate User
```http
DELETE /users/{user_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "message": "User deactivated successfully"
}
```

## 4. Content Creation & Management APIs

### 4.1 Posts

#### List Posts
```http
GET /posts
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
?page=1&limit=20&status=draft&created_by=user_uuid

Response: 200
{
  "posts": [
    {
      "id": "post_uuid",
      "title": "My Post Title",
      "content": {
        "text": "Post content here",
        "media_ids": ["media_uuid_1", "media_uuid_2"]
      },
      "channels": [
        {
          "platform": "facebook",
          "account_id": "fb_account_uuid",
          "customizations": {
            "text": "Facebook-specific content"
          }
        }
      ],
      "status": "draft",
      "created_by": "user_uuid",
      "created_at": "2024-01-01T00:00:00Z",
      "scheduled_at": "2024-01-02T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

#### Create Post
```http
POST /posts
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "title": "New Post Title",
  "content": {
    "text": "Base post content",
    "media_ids": ["media_uuid_1"]
  },
  "channels": [
    {
      "platform": "facebook",
      "account_id": "fb_account_uuid",
      "customizations": {
        "text": "Facebook version of content"
      }
    },
    {
      "platform": "twitter",
      "account_id": "twitter_account_uuid",
      "customizations": {
        "text": "Twitter version - shorter content"
      }
    }
  ],
  "scheduled_at": "2024-01-02T14:00:00Z"
}

Response: 201
{
  "id": "post_uuid",
  "title": "New Post Title",
  "status": "draft",
  "created_by": "user_uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Post
```http
PUT /posts/{post_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "title": "Updated Post Title",
  "content": {
    "text": "Updated content"
  }
}

Response: 200
{
  "id": "post_uuid",
  "title": "Updated Post Title",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Delete Post
```http
DELETE /posts/{post_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "message": "Post deleted successfully"
}
```

### 4.2 Approval Workflow

#### Submit for Approval
```http
POST /posts/{post_id}/submit-approval
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "message": "Ready for review"
}

Response: 200
{
  "status": "pending_approval",
  "submitted_at": "2024-01-01T00:00:00Z",
  "approvers": ["approver_user_uuid"]
}
```

#### Approve/Reject Post
```http
POST /posts/{post_id}/review
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "action": "approve",
  "feedback": "Looks great!"
}

Response: 200
{
  "status": "approved",
  "reviewed_by": "approver_uuid",
  "reviewed_at": "2024-01-01T00:00:00Z"
}
```

## 5. Media Management APIs

### 5.1 Media Library

#### List Media
```http
GET /media
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
?page=1&limit=20&type=image&search=logo

Response: 200
{
  "media": [
    {
      "id": "media_uuid",
      "filename": "company-logo.png",
      "type": "image",
      "size": 245760,
      "url": "https://storage.supabase.co/v1/object/public/media/tenant_uuid/media_uuid",
      "thumbnail_url": "https://storage.supabase.co/v1/object/public/media/tenant_uuid/thumbnails/media_uuid",
      "metadata": {
        "width": 1200,
        "height": 800,
        "format": "png"
      },
      "tags": ["logo", "branding"],
      "uploaded_by": "user_uuid",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 89,
    "total_pages": 5
  }
}
```

#### Upload Media
```http
POST /media/upload
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
Content-Type: multipart/form-data

file: <binary_file_data>
tags: ["product", "summer"]
description: "Summer product showcase"

Response: 201
{
  "id": "media_uuid",
  "filename": "uploaded-image.jpg",
  "type": "image",
  "size": 1024000,
  "url": "https://storage.supabase.co/v1/object/public/media/tenant_uuid/media_uuid",
  "uploaded_by": "user_uuid",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Generate AI Image
```http
POST /media/generate-ai
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "prompt": "Modern office workspace with plants",
  "style": "photographic",
  "size": "1024x1024"
}

Response: 201
{
  "id": "media_uuid",
  "filename": "ai-generated-office.jpg",
  "type": "image",
  "url": "https://storage.supabase.co/v1/object/public/media/tenant_uuid/media_uuid",
  "generation_prompt": "Modern office workspace with plants",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Media
```http
PUT /media/{media_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "tags": ["updated", "tag"],
  "description": "Updated description"
}

Response: 200
{
  "id": "media_uuid",
  "tags": ["updated", "tag"],
  "description": "Updated description",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Delete Media
```http
DELETE /media/{media_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "message": "Media deleted successfully"
}
```

## 6. Social Accounts Management APIs

### 6.1 Social Account Connection

#### List Connected Accounts
```http
GET /social-accounts
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "accounts": [
    {
      "id": "account_uuid",
      "platform": "facebook",
      "account_name": "My Business Page",
      "account_id": "facebook_page_id",
      "status": "connected",
      "permissions": ["publish_post", "read_insights"],
      "connected_at": "2024-01-01T00:00:00Z",
      "last_sync": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### Connect Social Account
```http
POST /social-accounts/connect
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "platform": "instagram",
  "auth_code": "oauth_authorization_code"
}

Response: 201
{
  "id": "account_uuid",
  "platform": "instagram",
  "account_name": "my_instagram_handle",
  "status": "connected",
  "connected_at": "2024-01-01T00:00:00Z"
}
```

#### Disconnect Social Account
```http
DELETE /social-accounts/{account_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "message": "Account disconnected successfully"
}
```

## 7. Scheduling & Publishing APIs

### 7.1 Content Calendar

#### Get Calendar View
```http
GET /calendar
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
?start_date=2024-01-01&end_date=2024-01-31&view=month

Response: 200
{
  "events": [
    {
      "post_id": "post_uuid",
      "title": "Post Title",
      "scheduled_at": "2024-01-15T10:00:00Z",
      "platforms": ["facebook", "instagram"],
      "status": "scheduled",
      "created_by": "user_uuid"
    }
  ],
  "summary": {
    "total_posts": 25,
    "published": 20,
    "scheduled": 5,
    "failed": 0
  }
}
```

#### Bulk Schedule Posts
```http
POST /posts/bulk-schedule
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
Content-Type: multipart/form-data

csv_file: <csv_file_data>

CSV Format:
title,content,platform,account_id,scheduled_at,media_urls
"Post 1","Content for post 1","facebook","fb_account_uuid","2024-01-15T10:00:00Z","https://media.url/image1.jpg"

Response: 201
{
  "imported": 50,
  "failed": 2,
  "errors": [
    {
      "row": 3,
      "error": "Invalid scheduled_at format"
    }
  ],
  "job_id": "bulk_job_uuid"
}
```

### 7.2 Publishing

#### Publish Post Now
```http
POST /posts/{post_id}/publish
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "post_id": "post_uuid",
  "status": "publishing",
  "platforms": [
    {
      "platform": "facebook",
      "status": "success",
      "platform_post_id": "fb_post_id",
      "published_at": "2024-01-01T00:00:00Z"
    },
    {
      "platform": "instagram",
      "status": "failed",
      "error": "Insufficient permissions"
    }
  ]
}
```

#### Revoke/Delete Published Post
```http
POST /posts/{post_id}/revoke
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "platforms": ["facebook", "twitter"]
}

Response: 200
{
  "post_id": "post_uuid",
  "revocation_results": [
    {
      "platform": "facebook",
      "status": "success",
      "deleted_at": "2024-01-01T00:00:00Z"
    },
    {
      "platform": "twitter",
      "status": "failed",
      "error": "Post not found on platform"
    }
  ]
}
```

## 8. Analytics & Reporting APIs

### 8.1 Performance Analytics

#### Get Post Performance
```http
GET /analytics/posts/{post_id}
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "post_id": "post_uuid",
  "overall_metrics": {
    "total_reach": 15000,
    "total_engagement": 450,
    "engagement_rate": 3.0,
    "clicks": 75
  },
  "platform_breakdown": [
    {
      "platform": "facebook",
      "reach": 10000,
      "engagement": 300,
      "likes": 250,
      "shares": 30,
      "comments": 20,
      "clicks": 50
    },
    {
      "platform": "instagram",
      "reach": 5000,
      "engagement": 150,
      "likes": 120,
      "comments": 30,
      "clicks": 25
    }
  ]
}
```

#### Get Dashboard Analytics
```http
GET /analytics/dashboard
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>
?date_range=last_30_days

Response: 200
{
  "overview": {
    "total_posts": 45,
    "total_reach": 500000,
    "total_engagement": 15000,
    "avg_engagement_rate": 3.2
  },
  "platform_performance": [
    {
      "platform": "facebook",
      "posts": 20,
      "reach": 300000,
      "engagement": 9000,
      "engagement_rate": 3.0
    }
  ],
  "top_performing_posts": [
    {
      "post_id": "post_uuid",
      "title": "Best Performing Post",
      "engagement": 1200,
      "reach": 25000
    }
  ],
  "engagement_trends": [
    {
      "date": "2024-01-01",
      "engagement": 450
    }
  ]
}
```

#### Get Insights & Recommendations
```http
GET /analytics/insights
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "insights": [
    {
      "type": "best_posting_time",
      "platform": "instagram",
      "recommendation": "Posts perform 40% better when published at 2 PM on weekdays",
      "confidence": 0.85
    },
    {
      "type": "content_type",
      "recommendation": "Video posts generate 60% more engagement than image posts",
      "confidence": 0.92
    }
  ],
  "audience_insights": {
    "demographics": {
      "age_groups": {
        "18-24": 0.25,
        "25-34": 0.35,
        "35-44": 0.30,
        "45+": 0.10
      },
      "top_locations": ["New York", "Los Angeles", "Chicago"]
    },
    "engagement_patterns": {
      "best_days": ["Tuesday", "Wednesday", "Thursday"],
      "best_hours": [14, 15, 19, 20]
    }
  }
}
```

## 9. AI Assistant APIs

### 9.1 Content Generation

#### Generate Content Suggestions
```http
POST /ai/content-suggestions
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "prompt": "Create a post about our new product launch",
  "platform": "instagram",
  "tone": "professional",
  "max_length": 280
}

Response: 200
{
  "suggestions": [
    {
      "content": "🚀 Excited to introduce our latest innovation! This new product will revolutionize your daily routine. #NewProduct #Innovation",
      "confidence": 0.92,
      "hashtags": ["#NewProduct", "#Innovation", "#TechLaunch"]
    }
  ],
  "usage": {
    "tokens_used": 150,
    "monthly_limit": 10000,
    "remaining": 9850
  }
}
```

#### Optimize Content for Platform
```http
POST /ai/optimize-content
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "content": "Check out our amazing new product that will change everything!",
  "source_platform": "facebook",
  "target_platform": "twitter"
}

Response: 200
{
  "optimized_content": "🔥 New product alert! This game-changer will transform your workflow. Get yours now! #Innovation #ProductLaunch",
  "changes_made": [
    "Added emojis for Twitter engagement",
    "Reduced length to fit character limit",
    "Added relevant hashtags"
  ]
}
```

## 10. Workflow Management APIs

### 10.1 Approval Workflows

#### List Workflows
```http
GET /workflows
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

Response: 200
{
  "workflows": [
    {
      "id": "workflow_uuid",
      "name": "Standard Approval",
      "description": "All posts require manager approval",
      "steps": [
        {
          "order": 1,
          "type": "approval",
          "approvers": ["manager_user_uuid"],
          "required": true
        }
      ],
      "is_default": true,
      "created_by": "admin_uuid",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Create Workflow
```http
POST /workflows
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "name": "High-Value Content Approval",
  "description": "Multi-stage approval for important posts",
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
      "approvers": ["brand_manager_uuid"],
      "required": true
    }
  ]
}

Response: 201
{
  "id": "workflow_uuid",
  "name": "High-Value Content Approval",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## 11. Webhooks & Events

### 11.1 Webhook Configuration

#### Register Webhook
```http
POST /webhooks
Authorization: Bearer <jwt_token>
X-Tenant-ID: <tenant_uuid>

{
  "url": "https://your-app.com/webhooks/omnipush",
  "events": ["post.published", "post.failed", "approval.required"],
  "secret": "webhook_secret_key"
}

Response: 201
{
  "id": "webhook_uuid",
  "url": "https://your-app.com/webhooks/omnipush",
  "events": ["post.published", "post.failed", "approval.required"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 11.2 Webhook Events

#### Post Published Event
```json
{
  "event": "post.published",
  "data": {
    "post_id": "post_uuid",
    "tenant_id": "tenant_uuid",
    "platforms": [
      {
        "platform": "facebook",
        "platform_post_id": "fb_post_id",
        "published_at": "2024-01-01T00:00:00Z"
      }
    ]
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Rate Limits

- **Authentication**: 100 requests/minute
- **Content Operations**: 1000 requests/hour
- **Analytics**: 500 requests/hour
- **AI Operations**: Based on subscription tier
- **Media Upload**: 100 uploads/hour

## Subscription Tier Limits

### Basic Tier
- Users: 3
- Posts per month: 100
- AI generations: 10
- Storage: 10GB

### Pro Tier
- Users: 10
- Posts per month: 1000
- AI generations: 100
- Storage: 50GB

### Enterprise Tier
- Users: Unlimited
- Posts per month: Unlimited
- AI generations: 1000
- Storage: 500GB

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden (insufficient permissions or tenant access)
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

## Data Types

### Post Status
- `draft` - Post is being created
- `pending_approval` - Submitted for approval
- `approved` - Approved and ready to schedule
- `scheduled` - Scheduled for future publication
- `publishing` - Currently being published
- `published` - Successfully published
- `failed` - Publication failed
- `rejected` - Rejected during approval

### User Roles
- `admin` - Full tenant management access
- `editor` - Content approval and management
- `creator` - Content creation and drafting
- `analyst` - Read-only analytics access

### Platforms
- `facebook`
- `instagram` 
- `twitter`
- `linkedin`
- `youtube`
- `tiktok`
- `pinterest`