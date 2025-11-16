# SMART RADAR Testing Guide

## Testing Strategy

This directory contains all test files and debugging scripts for the SMART RADAR application.

## Test Structure

```
tests/
├── backend/
│   ├── unit/           # Unit tests for services and models
│   ├── integration/    # API endpoint tests
│   └── fixtures/       # Test data fixtures
├── frontend/
│   ├── unit/           # Vue component tests
│   ├── integration/    # Store and service tests
│   └── e2e/            # End-to-end tests
├── data/               # Sample data for testing
└── scripts/            # Debug and utility scripts
```

## Running Tests

### Backend Tests
```bash
cd backend

# Install test dependencies
uv pip install pytest pytest-asyncio httpx

# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/unit/test_cluster_service.py

# Run with coverage
uv run pytest --cov=app tests/
```

### Frontend Tests
```bash
cd frontend

# Run unit tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run E2E tests
npm run test:e2e
```

## Test Categories

### Unit Tests
- Service layer business logic
- Data model validation
- Utility functions
- Vue component behavior

### Integration Tests
- API endpoint functionality
- Database operations
- WebSocket communication
- Store state management

### End-to-End Tests
- Complete user workflows
- Cross-component interaction
- Real-time features
- Response generation flow

## Sample Test Data

### Clusters
```json
{
  "name": "Test Healthcare Cluster",
  "cluster_type": "competitor",
  "keywords": ["#TestHealth", "@testuser"],
  "thresholds": {
    "twitter": {
      "min_likes": 100
    }
  },
  "is_active": true
}
```

### Narratives
```json
{
  "name": "Test Counter-Narrative",
  "language": "English",
  "talking_points": [
    "Test fact point one",
    "Test statistic reference"
  ],
  "is_active": true
}
```

### Social Posts
```json
{
  "platform": "twitter",
  "platform_post_id": "test123",
  "cluster_type": "competitor",
  "author": {
    "username": "testuser"
  },
  "content": {
    "text": "Test post content for testing"
  },
  "engagement": {
    "likes": 150
  },
  "intelligence": {
    "sentiment_score": -0.7,
    "sentiment_label": "Negative",
    "is_threat": true
  },
  "post_url": "https://twitter.com/test/123",
  "posted_at": "2024-01-01T12:00:00Z"
}
```

## Debug Scripts

### Database Utilities
```bash
# Reset test database
python tests/scripts/reset_db.py

# Seed test data
python tests/scripts/seed_data.py

# Export data for analysis
python tests/scripts/export_data.py
```

### API Testing
```bash
# Test all endpoints
python tests/scripts/test_api.py

# Load test with sample data
python tests/scripts/load_test.py
```

### WebSocket Testing
```bash
# Test real-time connections
node tests/scripts/test_websocket.js
```

## Mocking and Fixtures

### External Services
- Mock OpenAI API responses
- Mock social media API calls
- Test WebSocket connections
- Database fixtures

### Test Environment
```bash
# Test environment variables
MONGODB_URL=mongodb://localhost:27017/smart_radar_test
OPENAI_API_KEY=test_key
TESTING=true
```

## Coverage Goals

- Backend: >90% code coverage
- Frontend: >85% component coverage
- Critical paths: 100% coverage
- API endpoints: 100% coverage

## Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv pip install -r requirements.txt
          uv pip install pytest pytest-asyncio httpx
      - name: Run tests
        run: |
          cd backend
          uv run pytest
```

## Performance Testing

### Load Testing
- Test API response times under load
- Database query performance
- WebSocket connection limits
- Memory usage patterns

### Benchmarks
- Response generation time
- Database query optimization
- Frontend rendering performance
- Real-time update latency

## Test Data Management

### Test Database
- Separate test database instance
- Reset between test runs
- Isolated test collections
- Cleanup after tests

### Sample Datasets
- Various cluster configurations
- Different narrative strategies
- Diverse social media posts
- Multiple threat scenarios

## Debugging Tools

### Backend Debugging
```python
# Debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Database inspection
from app.core.database import get_database
db = get_database()
```

### Frontend Debugging
```javascript
// Vue devtools
// Component inspection
// Store state monitoring
// WebSocket message tracking
```

## Test Automation

### Pre-commit Hooks
- Run tests before commits
- Code formatting checks
- Import sorting
- Type checking

### Scheduled Tests
- Nightly full test suite
- Weekly integration tests
- Monthly performance benchmarks
- Quarterly security scans