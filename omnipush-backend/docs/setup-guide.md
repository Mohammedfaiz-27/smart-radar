# OmniChannel Content Orchestrator - Setup Guide

## Prerequisites

- Python 3.12+
- Supabase project
- Redis server (for Celery background tasks)
- Optional: OpenAI API key for AI features
- Optional: Stripe account for billing

## Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
# or using uv
uv sync
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up Supabase database**:
   - Create a new Supabase project
   - Run the SQL schema from `docs/database-schema.md`
   - Configure Row Level Security policies

4. **Start the application**:
```bash
# Development mode
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Environment Variables

### Required
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key
JWT_SECRET_KEY=your-super-secret-key-here
```

### Optional
```
# OpenAI for AI features
OPENAI_API_KEY=your-openai-api-key

# Stripe for billing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Redis for background tasks
REDIS_URL=redis://localhost:6379/0

# CORS origins
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## Database Setup

1. **Create tables** using the schema in `docs/database-schema.md`

2. **Enable Row Level Security**:
```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE media ENABLE ROW LEVEL SECURITY;
-- ... etc for all tables
```

3. **Create RLS policies**:
```sql
-- Example policy for users table
CREATE POLICY "Users can only access their tenant data" ON users
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Similar policies for all tenant-scoped tables
```

## API Documentation

Once running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication Flow

1. **Sign up**: `POST /v1/auth/signup`
   - Creates user and tenant
   - Returns access and refresh tokens

2. **Sign in**: `POST /v1/auth/signin` 
   - Returns access and refresh tokens

3. **Make API calls**: Include headers:
   ```
   Authorization: Bearer <access_token>
   X-Tenant-ID: <tenant_uuid>
   ```

## Testing the API

### 1. Create a tenant and user
```bash
curl -X POST "http://localhost:8000/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123",
    "tenant_name": "My Company",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### 2. Create a post
```bash
curl -X POST "http://localhost:8000/v1/posts" \
  -H "Authorization: Bearer <your_access_token>" \
  -H "X-Tenant-ID: <your_tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "content": {
      "text": "Hello, world! This is my first post.",
      "media_ids": []
    },
    "channels": [
      {
        "platform": "facebook",
        "account_id": "mock_fb_account",
        "customizations": {}
      }
    ]
  }'
```

## Background Tasks

For production deployment, run Celery workers:

```bash
# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A app.celery_app beat --loglevel=info
```

## Deployment

### Using Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - redis
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

## Monitoring

### Health Checks
- **API Health**: `GET /health`
- **Database Health**: Included in health check

### Logging
- Configure structured logging in production
- Use log aggregation (ELK stack, etc.)

### Metrics
- FastAPI metrics with Prometheus
- Supabase built-in metrics
- Custom business metrics

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check Supabase URL and keys
   - Verify network connectivity

2. **JWT token invalid**
   - Check JWT_SECRET_KEY matches
   - Verify token hasn't expired

3. **Tenant access denied**
   - Verify X-Tenant-ID header
   - Check user belongs to tenant

4. **RLS policies blocking queries**
   - Use service key for admin operations
   - Check RLS policy configuration

### Debug Mode

Set `DEBUG=true` in environment for verbose logging:
```bash
export DEBUG=true
uvicorn app:app --reload
```