# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniChannel Content Orchestrator - A multi-tenant SaaS platform for marketing teams to manage social media content lifecycle from creation to analytics.

**Tech Stack**: FastAPI backend, Supabase database with Row Level Security (RLS)
**Architecture**: Multi-tenant with strict data isolation using tenant_id foreign keys and RLS policies

## Development Commands

### Backend (FastAPI)
```bash
# Install dependencies with uv (preferred)
uv sync

# Start development server
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Alternative start methods
python run.py  # Uses uvicorn with reload
uv run python run.py

# Run tests
uv run pytest

# Code formatting and linting
uv run black .
uv run isort .
uv run flake8 .

# Type checking
uv run mypy .
```

### Database Management
```bash
# Apply consolidated schema
psql -f schema/consolidated_omnipush_schema.sql

# Apply individual migrations (in order)
psql -f schema/add_s3_keys_support.sql
psql -f schema/add_channel_tone_instructions.sql
```

## Architecture Overview

### Multi-Tenant Data Model
The system uses a shared database with tenant isolation enforced through:
- **tenant_id** foreign keys on all user data tables
- **Row Level Security (RLS)** policies in Supabase for automatic filtering  
- **JWT middleware** (`core/middleware.py`) that validates tenant membership
- **X-Tenant-ID** header requirement for authenticated requests

### API Architecture
- **FastAPI** with async/await for high performance
- **Pydantic** models for request/response validation in `models/`
- **JWT authentication** with refresh tokens via `core/security.py`
- **Modular API structure** in `api/v1/` with endpoints for:
  - Authentication (`auth.py`)
  - Tenant management (`tenants.py`) 
  - User management (`users.py`)
  - Content/posts (`posts.py`)
  - Media library (`media.py`)
  - Social accounts (`social.py`)
  - Analytics (`analytics.py`)
  - AI assistance (`ai.py`)
  - Workflows (`workflows.py`)
  - Webhooks (`webhooks.py`)
  - News automation (`news_items.py`, `pipelines.py`)
  - Content moderation (`moderation.py`)

### Legacy vs New API Structure
The codebase includes both:
- **Legacy endpoints** in `app.py` for backward compatibility (research, content generation)
- **New structured API** in `api/v1/` - preferred for new development
- **Services layer** in `services/` contains business logic used by both

### Database Schema Management
- **Consolidated schema**: `schema/consolidated_omnipush_schema.sql` (complete database structure)
- **Migration scripts**: Individual SQL files in `schema/` for incremental changes
- **RLS policies**: Implemented for strict tenant data isolation
- All schema changes should be added as migration scripts to `schema/` folder

## Key Architecture Principles

### Multi-Tenancy Security
- **Critical**: All data must be strictly isolated by tenant using `tenant_id` foreign keys
- Use RLS policies in Supabase for automatic tenant filtering
- All API endpoints require `X-Tenant-ID` header and validate tenant membership via middleware
- Media library must be tenant-scoped (no cross-tenant asset access)
- Social media account connections are per-tenant

### Authentication Flow
- JWT tokens with refresh token rotation via `core/security.py`
- Tenant context established through middleware (`core/middleware.py`)
- Current user available via `get_current_user()` dependency
- Tenant context via `get_tenant_context()` dependency

## Important File Locations

### Core Architecture
- `app.py` - Main FastAPI application with legacy endpoints
- `api/v1/api.py` - API router aggregation for new endpoints
- `core/middleware.py` - Authentication and tenant context middleware
- `core/config.py` - Application settings using Pydantic Settings
- `core/database.py` - Supabase client configuration
- `core/security.py` - JWT token handling

### Business Logic
- `services/` - Service layer with business logic (used by both legacy and new APIs)
- `models/` - Pydantic models for request/response validation
- `config/prompts.py` - AI prompt configurations

### Database & Schema
- `schema/consolidated_omnipush_schema.sql` - Complete database schema
- `schema/` - Migration scripts for incremental changes

## Environment Configuration
- `.env` file with Supabase credentials, API keys, and service configurations
- Required variables: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `JWT_SECRET_KEY`
- Optional: `OPENAI_API_KEY`, `NEWS_API_KEY`, `STRIPE_SECRET_KEY`, social media API keys

## Development Guidelines

### Code Organization
- Keep files under 300 lines (modular, reusable code)
- Use async/await patterns throughout FastAPI endpoints
- Follow Pydantic model patterns for data validation
- Place business logic in `services/` layer, not directly in API endpoints

### Database Changes
- Add migration script to `schema/` folder
- Update `schema/consolidated_omnipush_schema.sql` with changes
- Ensure RLS policies are included for new tenant data tables
- Test with multiple tenants to verify data isolation

### Multi-Tenant Development
- Always include `tenant_id` in data queries and inserts
- Use middleware dependencies: `get_current_user()` and `get_tenant_context()`
- Test API endpoints with different tenant contexts
- Verify RLS policies prevent cross-tenant data access

## User Roles & Permissions
- **tenant_admin**: Full workspace management, billing, user management
- **admin**: Content management, user invitations
- **editor**: Content review and approval
- **creator**: Content creation, drafting posts  
- **analyst**: Read-only access to analytics and reporting

## Development Notes
- The system supports background job processing with Celery/Redis for scheduled posts
- AI features (OpenAI integration) are optional and controlled by API key availability
- Social media integrations support Facebook, Instagram, Twitter, LinkedIn, WhatsApp
- News automation system (`pipelines.py`) supports automated content fetching and processing
- Content moderation system provides AI-powered content filtering