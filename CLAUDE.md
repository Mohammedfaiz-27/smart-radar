# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SMART RADAR MVP is a real-time social media intelligence platform designed as a Digital Command Center to monitor, analyze, and respond to online narratives. The system follows a 5-step workflow: Define Scope → Collect & Analyze → Prepare Responses → Visualize & Alert → Take Action.

## Technology Stack

- **Frontend**: Vue.js 3.4+ with Composition API
- **Backend**: Python 3.11+ with UV package manager, FastAPI
- **Database**: MongoDB 7.0+
- **Real-time**: WebSocket for live updates
- **AI**: OpenAI GPT for response generation

## Project Structure

```
smart-radar/
├── /docs/              # All documentation
├── /tests/             # Test and debug scripts  
├── /frontend/          # Vue.js application
│   ├── /src/components/    # Reusable UI components (PostCard, PostFeed, etc.)
│   ├── /src/stores/        # Pinia state management (posts, response, websocket, notifications)
│   ├── /src/services/      # API communication layer
│   ├── /src/router/        # Vue Router configuration
│   ├── /src/composables/   # Vue composition functions
│   └── /src/assets/        # Static assets
├── /backend/           # Python FastAPI application
│   ├── /app/models/        # MongoDB data models (Cluster, Narrative, SocialPost, ResponseLog)
│   ├── /app/api/           # REST API endpoints
│   ├── /app/services/      # Business logic layer
│   ├── /app/core/          # Database connection and config
│   ├── main.py             # FastAPI application entry point
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment configuration
├── docker-compose.yml
└── README.md
```

## Core Data Models

1. **Clusters**: Define keyword tracking scope (own/competitor organizations)
2. **Narratives**: Strategic talking points for response generation
3. **Social Posts**: Collected posts with AI sentiment analysis
4. **Response Logs**: Generated AI responses and their usage

## Development Commands

### Quick Start (All Services)
```bash
# Start all services with automated startup script
./start_workers.sh

# OR use Docker for full stack development
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up --build
```

### Backend (Python with UV)
```bash
cd backend

# Setup environment
uv venv
uv pip install -r requirements.txt

# Run development server
uv run python main.py

# Alternative
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker for background tasks
uv run celery -A app.core.celery_app worker --loglevel=info

# Run Celery Beat scheduler for automatic collection
uv run celery -A app.core.celery_app beat --loglevel=info
```

### Frontend (Vue.js)
```bash
cd frontend

# Install dependencies
npm install

# Run development server (localhost:3000 in Docker, localhost:5173 in local dev)
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Run linting with auto-fix
npm run lint

# Preview production build
npm run preview
```

### Database
```bash
# MongoDB runs on port 27017
# Access: mongodb://admin:password@localhost:27017/smart_radar?authSource=admin
# Celery now uses MongoDB as broker and result backend (no Redis required)
```

## API Endpoints

### Core APIs
- **Clusters**: `/api/v1/clusters/` - CRUD for keyword tracking
- **Narratives**: `/api/v1/narratives/` - CRUD for response templates  
- **Posts**: `/api/v1/posts/` - Social media content retrieval
- **Responses**: `/api/v1/responses/` - AI response generation
- **Data Collection**: `/api/v1/collection/` - Manual data collection triggers
- **Collection Config**: `/api/v1/collection-config/` - Control automatic collection settings
- **WebSocket**: `/ws` - Real-time updates

### Key API Patterns
- GET `/api/v1/posts?cluster_type=own` - Fetch organization posts
- GET `/api/v1/posts?cluster_type=competitor` - Fetch competitor posts
- GET `/api/v1/posts/threats` - High-priority threat posts
- POST `/api/v1/responses/generate` - Generate AI response

### Collection Configuration APIs
- GET `/api/v1/collection-config/config` - Get current collection settings
- POST `/api/v1/collection-config/config` - Update collection configuration
- POST `/api/v1/collection-config/disable-auto-collection` - Quickly disable automatic collection
- POST `/api/v1/collection-config/enable-auto-collection` - Quickly enable automatic collection
- GET `/api/v1/collection-config/status` - Get collection service status

## Frontend Architecture

### State Management (Pinia)
- **postsStore**: Manages social media posts and feeds
- **responseStore**: Handles AI response generation workflow  
- **notificationsStore**: Real-time alerts and notifications
- **websocketStore**: WebSocket connection management

### Key Components
- **Dashboard.vue**: Main command center with dual feeds
- **PostCard.vue**: Individual post display with response actions
- **ResponsePanel.vue**: Modal for AI response generation
- **ThreatAlerts.vue**: Critical post monitoring
- **NotificationCenter.vue**: Real-time alert system

### Component Communication
- Uses Pinia stores for state management
- Event-driven architecture with WebSocket updates
- Response panel triggered via `responseStore.openResponsePanel(post)`

## Backend Architecture

### Service Layer Pattern
- **ClusterService**: Business logic for keyword management
- **NarrativeService**: Strategic content management
- **SocialPostService**: Post collection and analysis
- **ResponseService**: AI-powered response generation
- **WebSocketManager**: Real-time client communication

### API Layer
Each service has corresponding FastAPI router in `/app/api/`

### Data Access Layer
MongoDB operations via Motor (async MongoDB driver)

## Key Features Implementation

### Real-time Dashboard
- Spatial separation: "Our Organization" vs "Competitors"  
- WebSocket updates for new posts and alerts
- Sentiment analysis display with color coding

### AI Response Generation
1. User clicks "Respond" on any post
2. Response panel opens with post context
3. User selects strategic narrative from dropdown
4. AI generates contextual response using OpenAI
5. User can copy response (auto-logs action)

### Threat Detection
- Posts flagged as threats based on sentiment + engagement
- Real-time alerts via WebSocket
- Dedicated threat monitoring section

## Environment Configuration

### Backend (.env)
```bash
MONGODB_URL=mongodb://admin:password@localhost:27017/smart_radar?authSource=admin
OPENAI_API_KEY=your_openai_api_key_here
DEBUG=true
CORS_ORIGINS=http://localhost:3000

# Automatic Data Collection Configuration
ENABLE_AUTO_COLLECTION=true
DATA_COLLECTION_INTERVAL_MINUTES=30
INTELLIGENCE_PROCESSING_INTERVAL_MINUTES=15
THREAT_MONITORING_INTERVAL_MINUTES=5
DAILY_ANALYTICS_ENABLED=true
WEEKLY_CLEANUP_ENABLED=true

# Note: Celery now uses MongoDB for broker and result backend (no Redis needed)
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### Docker Services
- **MongoDB**: Port 27017, credentials: admin/password
- **Backend**: Port 8000, FastAPI server
- **Frontend**: Port 3000, Vite dev server

## Code Standards

### Backend
- Follow SOLID principles and DRY methodology
- Use Pydantic models for data validation
- Async/await for all database operations
- Type hints throughout
- Error handling with proper HTTP status codes

### Frontend  
- Vue 3 Composition API exclusively
- Pinia for state management
- Tailwind CSS for styling
- Component-based architecture
- ESLint for code quality with auto-fix
- Vitest for testing framework

## Testing Strategy

### Frontend Testing
```bash
cd frontend
npm run test        # Run Vitest tests
```

### Backend Testing
```bash
cd backend
uv run python -m pytest tests/    # Run pytest (if tests exist)
```

- Unit tests for service layer business logic
- Integration tests for API endpoints  
- Component tests for Vue.js components with Vitest
- E2E tests for critical user workflows

## Deployment Notes

- Use `docker-compose.yml` for local development
- MongoDB requires persistent volume for data
- Frontend builds to static files for production
- Backend serves via Uvicorn ASGI server

## Common Development Tasks

- **Add new data collection source**: Extend `SocialPostService` and add new platform enum
- **Create new response narrative**: Use Narratives management UI
- **Modify AI response logic**: Update `ResponseService._generate_ai_response()`
- **Add new alert criteria**: Extend threat detection in `SocialPostService.get_threat_posts()`

## Automatic Data Collection

The system includes configurable automatic data collection powered by Celery:

### Configuration
Automatic collection behavior is controlled via environment variables:
- `ENABLE_AUTO_COLLECTION` - Enable/disable automatic collection (default: true)
- `DATA_COLLECTION_INTERVAL_MINUTES` - How often to collect posts (default: 30 minutes)
- `INTELLIGENCE_PROCESSING_INTERVAL_MINUTES` - Process intelligence on new posts (default: 15 minutes)
- `THREAT_MONITORING_INTERVAL_MINUTES` - Monitor for threat posts (default: 5 minutes)
- `DAILY_ANALYTICS_ENABLED` - Run daily analytics aggregation (default: true)
- `WEEKLY_CLEANUP_ENABLED` - Clean up old data weekly (default: true)

### Runtime Control
Use the Collection Config API to control collection without restarting services:
```bash
# Get current configuration
curl http://localhost:8000/api/v1/collection-config/config

# Disable automatic collection
curl -X POST http://localhost:8000/api/v1/collection-config/disable-auto-collection

# Update collection intervals
curl -X POST http://localhost:8000/api/v1/collection-config/config \
  -H "Content-Type: application/json" \
  -d '{"data_collection_interval_minutes": 60}'
```

### Services Required
For automatic collection to work, you need:
1. **MongoDB** - Database and message broker for Celery (already configured)
2. **Celery Worker** - Process background tasks
3. **Celery Beat** - Schedule periodic tasks

Start all services manually:
```bash
# Terminal 1: FastAPI server
cd backend && uv run uvicorn main:app --reload

# Terminal 2: Celery worker
cd backend && uv run celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Celery Beat scheduler
cd backend && uv run celery -A app.core.celery_app beat --loglevel=info

# Terminal 4: Frontend (in separate terminal)
cd frontend && npm run dev
```

**Or use the automated startup script:**
```bash
./start_workers.sh
```

## Debugging & Troubleshooting

### Common Debug Commands
```bash
# Check MongoDB connection (used by both app and Celery)
mongosh "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Monitor Celery worker logs
cd backend && uv run celery -A app.core.celery_app worker --loglevel=debug

# Test API endpoints
curl http://localhost:8000/api/v1/posts
curl http://localhost:8000/docs  # Interactive API docs

# Monitor WebSocket connections (requires wscat)
npm install -g wscat
wscat -c ws://localhost:8000/ws
```

### Environment Setup Issues
```bash
# Backend environment setup
cd backend
cp .env.example .env  # Edit with your API keys

# Verify Python UV installation
uv --version

# Reinstall dependencies if needed
cd backend && uv pip install -r requirements.txt --force-reinstall

# Frontend dependency issues
cd frontend
rm -rf node_modules package-lock.json
npm install
```