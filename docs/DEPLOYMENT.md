# SMART RADAR Deployment Guide

## Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- UV package manager

### Quick Start with Docker

1. **Clone and start all services:**
```bash
git clone <repository>
cd smart-radar
docker-compose up -d
```

2. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- MongoDB: localhost:27017

### Manual Development Setup

#### Backend Setup
```bash
cd backend

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your OpenAI API key

# Start MongoDB (via Docker)
docker run -d -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  mongo:7.0

# Run backend server
uv run python main.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Environment Variables

### Backend (.env)
```bash
# Database
MONGODB_URL=mongodb://admin:password@localhost:27017/smart_radar?authSource=admin

# AI Service
OPENAI_API_KEY=your_openai_api_key_here

# Cache (optional)
REDIS_URL=redis://localhost:6379

# Application
DEBUG=true
PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### Frontend (.env)
```bash
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Production Deployment

### Docker Production Build

1. **Create production environment files:**
```bash
# backend/.env.production
MONGODB_URL=mongodb://username:password@mongodb-host:27017/smart_radar
OPENAI_API_KEY=your_production_openai_key
DEBUG=false
CORS_ORIGINS=https://your-domain.com

# frontend/.env.production
VITE_API_URL=https://api.your-domain.com
VITE_WS_URL=wss://api.your-domain.com/ws
```

2. **Build and deploy:**
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Deployment Options

#### Option 1: AWS ECS/Fargate
- Use AWS ECS for container orchestration
- Amazon DocumentDB for MongoDB
- Application Load Balancer for traffic distribution
- CloudFront for frontend CDN

#### Option 2: Google Cloud Run
- Deploy backend as Cloud Run service
- Use MongoDB Atlas for database
- Deploy frontend to Firebase Hosting or GCS

#### Option 3: DigitalOcean App Platform
- Deploy as multi-component app
- Use DigitalOcean Managed MongoDB
- Automatic SSL and CDN included

### Database Setup

#### MongoDB Atlas (Recommended for Production)
1. Create MongoDB Atlas cluster
2. Configure network access (whitelist IPs)
3. Create database user
4. Get connection string
5. Update MONGODB_URL in environment

#### Self-hosted MongoDB
```bash
# MongoDB with replica set for production
docker run -d \
  --name mongodb \
  --restart unless-stopped \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secure_password \
  mongo:7.0 --replSet rs0

# Initialize replica set
docker exec -it mongodb mongosh --eval "rs.initiate()"
```

## Monitoring and Logging

### Application Metrics
- Add Prometheus metrics endpoints
- Use Grafana for visualization
- Monitor API response times and error rates

### Logging Configuration
```python
# backend/app/core/logging.py
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
```

### Health Checks
- API health endpoint: `/health`
- Database connectivity check
- WebSocket connection validation

## Security Considerations

### API Security
- Implement API authentication (JWT tokens)
- Add rate limiting (Redis-based)
- Input validation and sanitization
- CORS configuration for production domains

### Database Security
- Use connection string with authentication
- Enable MongoDB authentication
- Regular backup schedule
- Network security (VPC/firewall rules)

### Environment Security
- Never commit `.env` files
- Use secrets management (AWS Secrets Manager, etc.)
- Rotate API keys regularly
- HTTPS only in production

## Backup and Recovery

### Database Backups
```bash
# MongoDB backup
mongodump --uri="mongodb://user:pass@host:27017/smart_radar" --out ./backup

# Restore
mongorestore --uri="mongodb://user:pass@host:27017/smart_radar" ./backup/smart_radar
```

### Automated Backups
- Daily automated backups to cloud storage
- Retention policy (keep 30 days)
- Test restore procedures monthly

## Scaling Considerations

### Backend Scaling
- Horizontal scaling with multiple API instances
- Load balancer with health checks
- Database connection pooling
- Cache frequently accessed data (Redis)

### Frontend Scaling
- CDN for static assets
- Gzip compression
- Bundle optimization
- Image optimization

### Database Scaling
- MongoDB replica sets for read scaling
- Sharding for write scaling
- Index optimization for queries
- Connection pooling

## Performance Optimization

### Backend Optimizations
- Database indexing strategy
- Async operations for I/O
- Response caching
- Background job processing (Celery)

### Frontend Optimizations
- Code splitting and lazy loading
- Component memoization
- Virtual scrolling for large lists
- Image lazy loading

## Troubleshooting

### Common Issues

**MongoDB Connection Failed:**
```bash
# Check MongoDB status
docker logs mongodb

# Test connection
mongosh "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"
```

**Frontend Build Errors:**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -i :3000
```

**Backend API Errors:**
```bash
# Check backend logs
docker logs smart-radar-backend

# Test API health
curl http://localhost:8000/health
```

### Log Analysis
- Monitor error rates and patterns
- Set up alerting for critical errors
- Use structured logging for better analysis

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Review and rotate API keys quarterly
- Database maintenance and optimization
- Security patch updates
- Performance monitoring review

### Upgrade Procedures
1. Test upgrades in staging environment
2. Backup database before upgrades
3. Rolling deployment for zero downtime
4. Rollback procedures documented
5. Post-upgrade validation checklist