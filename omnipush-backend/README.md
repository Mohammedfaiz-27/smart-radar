# OmniChannel Content Orchestrator

A comprehensive multi-tenant SaaS platform for managing social media content lifecycle from creation to analytics.

## 🚀 Features

### **Multi-Tenant Architecture**
- Secure tenant isolation with Row Level Security (RLS)
- Subscription-based access control (Basic, Pro, Enterprise)
- User roles: Admin, Editor, Creator, Analyst

### **Content Management**
- Multi-platform post creation and customization
- Rich media library with file upload and AI generation
- Approval workflows with configurable steps
- Bulk scheduling via CSV import

### **Social Media Integration**
- Connect multiple social accounts per platform
- Platform-specific content optimization
- Secure token storage with encryption
- Support for Facebook, Instagram, Twitter, LinkedIn, and more

### **AI-Powered Features**
- Content suggestions with customizable tone and platform optimization
- AI image generation (DALL-E integration)
- Content optimization across platforms
- Usage tracking and limits

### **Scheduling & Publishing**
- Visual content calendar
- Bulk publishing and scheduling
- Post revocation/deletion
- Background job processing with Celery

### **Analytics & Reporting**
- Performance metrics per post and platform
- Dashboard with engagement trends
- AI-powered insights and recommendations
- Data export (CSV, JSON)

### **Workflow Management**
- Configurable approval workflows
- Multi-step approval processes
- Role-based access control

### **Webhooks & Events**
- Real-time event notifications
- Configurable webhook endpoints
- Secure payload signing
- Event types: post published, failed, approval required

## 🏗️ Architecture

### **Tech Stack**
- **Backend**: FastAPI with Python 3.12+
- **Database**: Supabase (PostgreSQL) with RLS
- **Authentication**: JWT with refresh tokens
- **Background Tasks**: Celery with Redis
- **File Storage**: Supabase Storage (or cloud storage)
- **AI Services**: OpenAI GPT/DALL-E
- **Payments**: Stripe integration

### **Key Components**
```
├── api/v1/               # API endpoints
│   ├── auth.py          # Authentication
│   ├── tenants.py       # Tenant management
│   ├── users.py         # User management
│   ├── posts.py         # Content management
│   ├── media.py         # Media library
│   ├── social.py        # Social accounts
│   ├── scheduling.py    # Publishing & calendar
│   ├── analytics.py     # Analytics & reporting
│   ├── ai.py           # AI assistant
│   ├── workflows.py     # Approval workflows
│   └── webhooks.py      # Webhook management
├── core/                # Core functionality
│   ├── config.py        # Configuration
│   ├── database.py      # Supabase client
│   ├── security.py      # Authentication & JWT
│   └── middleware.py    # Auth & tenant middleware
├── models/              # Pydantic models
└── services/            # Legacy services (backward compatibility)
```

## 🚀 Quick Start

### **1. Clone and Install**
```bash
git clone <repository-url>
cd omnipush-backend
pip install -r requirements.txt
```

### **2. Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

### **3. Set Up Database**
- Create Supabase project
- Run SQL schema from `docs/database-schema.md`
- Configure RLS policies

### **4. Start Application**
```bash
# Development
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### **5. Start Background Workers** (Optional)
```bash
# Redis server
redis-server

# Celery worker
celery -A app.celery_app worker --loglevel=info

# Celery beat scheduler
celery -A app.celery_app beat --loglevel=info
```

## 📚 Documentation

- **[Setup Guide](docs/setup-guide.md)** - Detailed setup instructions
- **[API Examples](docs/api-examples.md)** - Practical API usage examples
- **[Database Schema](docs/database-schema.md)** - Complete database structure
- **[API Specification](docs/api-specification.md)** - Full API documentation

### **Interactive API Docs**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication

### **Sign Up (Creates Tenant)**
```bash
POST /v1/auth/signup
{
  "email": "admin@example.com",
  "password": "securepassword123",
  "tenant_name": "My Company",
  "first_name": "John",
  "last_name": "Doe"
}
```

### **Make Authenticated Requests**
```bash
curl -H "Authorization: Bearer <token>" \
     -H "X-Tenant-ID: <tenant_id>" \
     http://localhost:8000/v1/posts
```

## 🌟 Key Features Deep Dive

### **Multi-Platform Content**
Create one post, customize for each platform:
```json
{
  "title": "Product Launch",
  "content": {"text": "Base content"},
  "channels": [
    {
      "platform": "facebook",
      "customizations": {"text": "Facebook-specific version"}
    },
    {
      "platform": "twitter", 
      "customizations": {"text": "Twitter version"}
    }
  ]
}
```

### **AI Content Generation**
```bash
POST /v1/ai/content-suggestions
{
  "prompt": "Product launch for eco-friendly bottles",
  "platform": "instagram",
  "tone": "enthusiastic"
}
```

### **Bulk Scheduling**
Upload CSV with posts:
```csv
title,content,platform,account_id,scheduled_at
"Post 1","Content 1","facebook","account_id","2024-07-15T10:00:00Z"
```

### **Real-time Webhooks**
```bash
POST /v1/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["post.published", "post.failed"],
  "secret": "webhook_secret"
}
```

## 🚦 API Endpoints Overview

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Auth** | `/v1/auth/*` | Sign up, sign in, refresh tokens |
| **Tenants** | `/v1/tenants/*` | Tenant management, subscriptions |
| **Users** | `/v1/users/*` | User management, invitations |
| **Posts** | `/v1/posts/*` | Content creation, management |
| **Media** | `/v1/media/*` | File uploads, AI generation |
| **Social** | `/v1/social-accounts/*` | Connect social accounts |
| **Calendar** | `/v1/calendar/*` | Scheduling, publishing |
| **Analytics** | `/v1/analytics/*` | Performance, insights |
| **AI** | `/v1/ai/*` | Content generation, optimization |
| **Workflows** | `/v1/workflows/*` | Approval processes |
| **Webhooks** | `/v1/webhooks/*` | Event notifications |

## 🔒 Security Features

- **Multi-tenant data isolation** with RLS
- **JWT authentication** with refresh tokens
- **Role-based access control** (RBAC)
- **Encrypted token storage** for social accounts
- **Webhook signature verification**
- **Rate limiting** and usage tracking

## 📊 Subscription Tiers

| Feature | Basic | Pro | Enterprise |
|---------|-------|-----|------------|
| Users | 3 | 10 | Unlimited |
| Posts/month | 100 | 1,000 | Unlimited |
| AI Generations | 10 | 100 | 1,000 |
| Storage | 10GB | 50GB | 500GB |

## 🚀 Deployment

### **Docker**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Docker Compose**
```yaml
version: '3.8'
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
  
  redis:
    image: redis:alpine
    
  worker:
    build: .
    command: celery -A app.celery_app worker
```

## 🧪 Testing

```bash
# Run tests
pytest

# Test specific endpoint
pytest tests/test_auth.py

# Load testing
locust -f tests/locust_test.py
```

## 📈 Monitoring

- **Health checks**: `/health`
- **Metrics**: Prometheus integration
- **Logging**: Structured JSON logs
- **Error tracking**: Sentry integration

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: `/docs` folder
- **API Docs**: http://localhost:8000/docs
- **Issues**: GitHub Issues
- **Email**: support@omnipush.com

---

**Built with ❤️ for social media marketers and agencies**