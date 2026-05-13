-- =====================================================
-- OmniPush Platform - Consolidated Database Schema
-- =====================================================
-- This consolidated schema includes all database components for the OmniPush platform
-- Multi-tenant SaaS platform for social media content orchestration
-- Execution order optimized for dependencies and data integrity
-- Last updated: 2025-01-15
-- Added: llm_logs table for LLM API tracking and analytics

-- =====================================================
-- CLEANUP COMMANDS (Run these first to clean existing data)
-- =====================================================

-- Drop all tables in reverse dependency order (CASCADE will drop policies automatically)
-- Level 4: Tables that depend on posts, social_accounts, pipelines
DROP TABLE IF EXISTS post_drafts CASCADE;
DROP TABLE IF EXISTS content_adaptations CASCADE;
DROP TABLE IF EXISTS media CASCADE;
DROP TABLE IF EXISTS post_analytics CASCADE;
DROP TABLE IF EXISTS scraper_job_runs CASCADE;
DROP TABLE IF EXISTS pipeline_runs CASCADE;
DROP TABLE IF EXISTS llm_logs CASCADE;

-- Level 3: Tables that depend on channel_groups, news_items, social_accounts
DROP TABLE IF EXISTS posts CASCADE;
DROP TABLE IF EXISTS social_media_content CASCADE;
DROP TABLE IF EXISTS social_sync_states CASCADE;
DROP TABLE IF EXISTS social_channel_template_assignments CASCADE;
DROP TABLE IF EXISTS facebook_pages_cache CASCADE;

-- Level 2: Tables that depend on tenants, users, pipelines
DROP TABLE IF EXISTS news_items CASCADE;
DROP TABLE IF EXISTS pipelines CASCADE;
DROP TABLE IF EXISTS scraper_jobs CASCADE;
DROP TABLE IF EXISTS background_tasks CASCADE;
DROP TABLE IF EXISTS cron_job_runs CASCADE;
DROP TABLE IF EXISTS cron_jobs CASCADE;
DROP TABLE IF EXISTS tenant_settings CASCADE;
DROP TABLE IF EXISTS facebook_user_accounts CASCADE;
DROP TABLE IF EXISTS usage_tracking CASCADE;
DROP TABLE IF EXISTS webhooks CASCADE;
DROP TABLE IF EXISTS workflows CASCADE;
DROP TABLE IF EXISTS invitations CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS channel_groups CASCADE;
DROP TABLE IF EXISTS newscard_templates CASCADE;
DROP TABLE IF EXISTS social_accounts CASCADE;

-- Level 1: Tables that depend only on tenants
DROP TABLE IF EXISTS users CASCADE;

-- Level 0: Base table
DROP TABLE IF EXISTS tenants CASCADE;

-- Drop custom types if they exist
DROP TYPE IF EXISTS draft_status CASCADE;
DROP TYPE IF EXISTS pipeline_status CASCADE;
DROP TYPE IF EXISTS processing_step CASCADE;
DROP TYPE IF EXISTS news_source CASCADE;
DROP TYPE IF EXISTS moderation_status CASCADE;
DROP TYPE IF EXISTS channel_type CASCADE;
DROP TYPE IF EXISTS subscription_tier CASCADE;
DROP TYPE IF EXISTS subscription_status CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS user_status CASCADE;
DROP TYPE IF EXISTS invitation_status CASCADE;
DROP TYPE IF EXISTS post_status CASCADE;
DROP TYPE IF EXISTS platform CASCADE;
DROP TYPE IF EXISTS media_type CASCADE;
DROP TYPE IF EXISTS account_status CASCADE;
DROP TYPE IF EXISTS webhook_event CASCADE;
DROP TYPE IF EXISTS workflow_step_type CASCADE;

-- =====================================================
-- CUSTOM ENUM TYPES
-- =====================================================

-- Subscription related enums
CREATE TYPE subscription_tier AS ENUM ('basic', 'pro', 'enterprise');
CREATE TYPE subscription_status AS ENUM ('active', 'inactive', 'canceled', 'past_due');

-- User related enums
CREATE TYPE user_role AS ENUM ('admin', 'editor', 'creator', 'analyst', 'tenant_admin');
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'pending');
CREATE TYPE invitation_status AS ENUM ('pending', 'accepted', 'expired');

-- Content related enums
CREATE TYPE post_status AS ENUM ('draft', 'pending_approval', 'approved', 'scheduled', 'publishing', 'published', 'failed', 'rejected');
CREATE TYPE platform AS ENUM ('facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'whatsapp');
CREATE TYPE draft_status AS ENUM ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED', 'FAILED');

-- Media related enums
CREATE TYPE media_type AS ENUM ('image', 'video', 'document');

-- Social accounts related enums
CREATE TYPE account_status AS ENUM ('connected', 'disconnected', 'error', 'expired');

-- Webhook related enums
CREATE TYPE webhook_event AS ENUM ('post.published', 'post.failed', 'approval.required', 'user.invited', 'subscription.changed');

-- Workflow related enums
CREATE TYPE workflow_step_type AS ENUM ('approval', 'review', 'notification');

-- Pipeline related enums
CREATE TYPE pipeline_status AS ENUM ('active', 'inactive', 'paused', 'error');
CREATE TYPE processing_step AS ENUM ('text', 'image', 'both');
CREATE TYPE news_source AS ENUM ('rss', 'api', 'webhook');
CREATE TYPE moderation_status AS ENUM ('pending', 'approved', 'rejected', 'flagged');
CREATE TYPE channel_type AS ENUM ('input', 'output');

-- =====================================================
-- CORE TABLES
-- =====================================================

-- Tenants table - Multi-tenant workspace information
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    subscription_tier subscription_tier NOT NULL DEFAULT 'basic',
    subscription_status subscription_status NOT NULL DEFAULT 'active',
    billing_email VARCHAR(255),
    slug VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table - User accounts with tenant association
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role user_role NOT NULL DEFAULT 'creator',
    status user_status NOT NULL DEFAULT 'active',
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email, tenant_id)
);

-- =====================================================
-- CONTENT MANAGEMENT TABLES
-- =====================================================

-- Channel Groups table - Organized groups of social media channels
CREATE TABLE channel_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#3b82f6',
    social_account_ids UUID[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Posts table - Content posts for social media
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    content JSONB NOT NULL,
    channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    status post_status NOT NULL DEFAULT 'draft',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    preview_html TEXT,
    news_card_url VARCHAR(500),
    channel_group_id UUID REFERENCES channel_groups(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    publish_results JSONB DEFAULT '{}',
    processing_task_id VARCHAR(255),
    error_message TEXT,
    keywords TEXT[] DEFAULT '{}',
    image_search_caption VARCHAR(500),
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Media table - Media files with tenant isolation
CREATE TABLE media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size INTEGER NOT NULL,
    size INTEGER,
    mime_type VARCHAR(100) NOT NULL,
    content_type TEXT NULL,
    media_type media_type NOT NULL,
    generation_prompt TEXT,
    metadata JSONB,
    s3_key VARCHAR(500),
    s3_bucket VARCHAR(100),
    thumbnail_s3_key VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT check_file_location CHECK (file_path IS NOT NULL OR s3_key IS NOT NULL)
);

-- =====================================================
-- SOCIAL MEDIA INTEGRATION
-- =====================================================

-- Social accounts table - Connected social media accounts
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    page_id VARCHAR(255) NULL,
    periskope_id VARCHAR(255) NULL,
    permissions TEXT[] DEFAULT '{}',
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    status account_status NOT NULL DEFAULT 'connected',
    content_tone VARCHAR(50) DEFAULT 'professional',
    custom_instructions TEXT,
    auto_image_search BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync TIMESTAMP WITH TIME ZONE,
    last_cursor TEXT,
    sync_config JSONB DEFAULT '{}',
    last_sync_status VARCHAR(50) DEFAULT 'success',
    sync_error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    account_link TEXT null,
    UNIQUE(platform, account_id, tenant_id)
);

-- Newscard templates metadata table
CREATE TABLE newscard_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(255) UNIQUE NOT NULL,
    template_display_name VARCHAR(255) NOT NULL,
    template_path VARCHAR(500) NOT NULL,
    s3_url VARCHAR(1000),
    s3_bucket VARCHAR(255),
    s3_key VARCHAR(500),
    supports_images BOOLEAN NOT NULL DEFAULT false,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Social channel template assignments table
CREATE TABLE social_channel_template_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    template_with_image VARCHAR(255),
    template_without_image VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    UNIQUE(tenant_id, social_account_id),
    CHECK (template_with_image IS NOT NULL OR template_without_image IS NOT NULL),
    CHECK (platform IN ('facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok', 'pinterest', 'whatsapp'))
);

-- Social media sync state table for detailed tracking
CREATE TABLE social_sync_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    sync_type VARCHAR(50) NOT NULL,
    last_cursor TEXT,
    last_sync_timestamp TIMESTAMP WITH TIME ZONE,
    last_item_id VARCHAR(255),
    sync_config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(social_account_id, sync_type)
);

-- Social media content table to store fetched content
CREATE TABLE social_media_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    platform_content_id VARCHAR(255) NOT NULL,
    content_data JSONB NOT NULL,
    author_id VARCHAR(255),
    author_name VARCHAR(255),
    content_text TEXT,
    media_urls TEXT[],
    engagement_metrics JSONB,
    published_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, platform_content_id)
);

-- =====================================================
-- FACEBOOK CACHE TABLES
-- =====================================================

-- Facebook User Accounts Cache
CREATE TABLE facebook_user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    facebook_user_id TEXT NOT NULL,
    user_access_token TEXT NOT NULL,
    token_type TEXT DEFAULT 'user',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, facebook_user_id)
);

-- Facebook Pages Cache
CREATE TABLE facebook_pages_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    facebook_user_account_id UUID NOT NULL REFERENCES facebook_user_accounts(id) ON DELETE CASCADE,
    page_id TEXT NOT NULL,
    page_name TEXT NOT NULL,
    page_access_token TEXT,
    category TEXT,
    category_list JSONB,
    tasks JSONB,
    access_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, facebook_user_account_id, page_id)
);

-- =====================================================
-- AUTOMATION SYSTEM
-- =====================================================

-- Cron jobs table
CREATE TABLE cron_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,
    task_type TEXT NOT NULL,
    parameters JSONB DEFAULT '{}',
    is_enabled BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    run_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cron job runs table
CREATE TABLE cron_job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES cron_jobs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tenant settings table
CREATE TABLE tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    news_automation JSONB DEFAULT '{}',
    social_automation JSONB DEFAULT '{}',
    analytics_settings JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Background tasks table - Task tracking and management
CREATE TABLE background_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    data JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    progress JSONB DEFAULT '{}'
);

-- =====================================================
-- CONTENT PIPELINE SYSTEM
-- =====================================================

-- Pipelines table - Content processing pipelines
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL,
    status pipeline_status NOT NULL DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_run TIMESTAMP WITH TIME ZONE,
    total_processed INTEGER DEFAULT 0
);

-- News items table - Content fetched and processed by pipelines
CREATE TABLE news_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    category VARCHAR(100),
    status VARCHAR(100),
    is_approved BOOLEAN DEFAULT FALSE,
    url TEXT,
    tenant_id UUID,
    published_at TIMESTAMP WITH TIME ZONE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    moderation_status moderation_status DEFAULT 'pending',
    moderation_score DECIMAL(3,2),
    moderation_flags TEXT[],
    moderation_reason TEXT,
    processed_content TEXT,
    generated_image_url VARCHAR(500),
    images JSONB,
    published_channels TEXT[],
    moderated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add relationship between posts and news items
ALTER TABLE posts ADD COLUMN IF NOT EXISTS news_item_id UUID REFERENCES news_items(id) ON DELETE SET NULL;

-- Pipeline runs table
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    items_processed INTEGER DEFAULT 0,
    items_published INTEGER DEFAULT 0,
    errors TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Social Media Scraper Jobs Configuration Table
CREATE TABLE scraper_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    platforms TEXT[] NOT NULL DEFAULT '{}',
    schedule_cron VARCHAR(100) NOT NULL DEFAULT '*/5 * * * *',
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    settings JSONB DEFAULT '{}',
    post_approval_logic TEXT,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Scraper Job Runs History Table
CREATE TABLE scraper_job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_job_id UUID NOT NULL REFERENCES scraper_jobs(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    posts_found INTEGER DEFAULT 0,
    posts_processed INTEGER DEFAULT 0,
    posts_approved INTEGER DEFAULT 0,
    posts_published INTEGER DEFAULT 0,
    error_message TEXT,
    run_log JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Social Account URLs for Scraper Jobs
CREATE TABLE scraper_job_social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_job_id UUID NOT NULL REFERENCES scraper_jobs(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_url TEXT NOT NULL,
    account_identifier VARCHAR(255),
    account_id VARCHAR(255),
    account_name VARCHAR(255),
    account_metadata JSONB DEFAULT '{}',
    resolution_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    resolution_error TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    last_validation_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_job_account UNIQUE(scraper_job_id, platform, account_url)
);

-- =====================================================
-- SUPPORTING TABLES
-- =====================================================

-- Subscriptions table - Subscription management
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(100) UNIQUE,
    stripe_customer_id VARCHAR(100),
    subscription_tier subscription_tier NOT NULL,
    subscription_status subscription_status NOT NULL,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invitations table - User invitations
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'creator',
    status invitation_status NOT NULL DEFAULT 'pending',
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflows table - Content approval workflows
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Webhooks table - External webhook configurations
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    events webhook_event[] NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    secret_key VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- ANALYTICS TABLES
-- =====================================================

-- Post analytics table - Analytics data for posts
CREATE TABLE post_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    platform platform NOT NULL,
    metrics JSONB NOT NULL,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage tracking table - API usage tracking
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    response_time INTEGER,
    status_code INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- LLM Logs Table for tracking all LLM API calls and responses
-- This provides observability, debugging, and usage analytics
CREATE TABLE llm_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,

    -- Request metadata
    profile VARCHAR(50) NOT NULL,  -- DEFAULT, PRECISE, CREATIVE, ANALYTICAL
    model VARCHAR(100) NOT NULL,   -- gpt-4o-mini, gpt-4o, etc.
    operation VARCHAR(50) NOT NULL, -- generate, stream, batch_generate

    -- Request parameters
    messages JSONB NOT NULL,       -- Array of message objects
    temperature NUMERIC(3,2),
    max_tokens INTEGER,
    additional_params JSONB,       -- Other parameters (top_p, frequency_penalty, etc.)

    -- Response data
    response_content TEXT,         -- Generated content
    response_metadata JSONB,       -- Token usage, model info, etc.

    -- Execution metrics
    status VARCHAR(20) NOT NULL DEFAULT 'success', -- success, error, partial
    error_message TEXT,
    execution_time_ms INTEGER,     -- Execution time in milliseconds

    -- Token tracking
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Service context
    service_name VARCHAR(100),     -- Which service made the call
    request_id VARCHAR(100),       -- Optional request tracking ID

    -- Indexing for common queries
    CONSTRAINT valid_status CHECK (status IN ('success', 'error', 'partial'))
);

-- Content adaptations tracking table
CREATE TABLE content_adaptations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    adapted_content_length INTEGER DEFAULT 0,
    hashtag_count INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Post drafts table for human-in-the-loop review of LLM-generated content
CREATE TABLE post_drafts (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Source tracking (either external news or regular post)
    external_news_id UUID REFERENCES external_news_items(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,

    -- Publishing target
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,

    -- LLM-generated content (immutable - what AI suggested)
    generated_content TEXT NOT NULL,
    generated_headline VARCHAR(100),
    generated_district VARCHAR(100),
    generated_hashtags TEXT[] DEFAULT '{}',

    -- User-editable content (final version to be published)
    final_content TEXT NOT NULL,
    final_headline VARCHAR(100),
    final_district VARCHAR(100),
    final_hashtags TEXT[] DEFAULT '{}',

    -- Workflow status
    status draft_status NOT NULL DEFAULT 'PENDING_REVIEW',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    rejection_reason TEXT,

    -- Publishing results
    published_at TIMESTAMP WITH TIME ZONE,
    publish_result JSONB,
    error_message TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT check_source_exists CHECK (
        (external_news_id IS NOT NULL AND post_id IS NULL) OR
        (external_news_id IS NULL AND post_id IS NOT NULL)
    ),
    CONSTRAINT valid_draft_status CHECK (status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED', 'FAILED'))
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Core entity indexes
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);

CREATE INDEX idx_posts_tenant_id ON posts(tenant_id);
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_by ON posts(created_by);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_scheduled_at ON posts(scheduled_at);
CREATE INDEX idx_posts_published_at ON posts(published_at);
CREATE INDEX idx_posts_channel_group_id ON posts(channel_group_id);
CREATE INDEX idx_posts_metadata ON posts USING GIN (metadata);
CREATE INDEX idx_posts_automation_source ON posts((metadata->>'source')) WHERE metadata->>'source' = 'automated_news';
CREATE INDEX idx_posts_publish_results ON posts USING GIN (publish_results);
CREATE INDEX idx_posts_processing_task_id ON posts(processing_task_id);
CREATE INDEX idx_posts_keywords ON posts USING GIN (keywords);
CREATE INDEX idx_posts_news_item_id ON posts(news_item_id);

CREATE INDEX idx_media_tenant_id ON media(tenant_id);
CREATE INDEX idx_media_post_id ON media(post_id);
CREATE INDEX idx_media_s3_key ON media(s3_key);
CREATE INDEX idx_media_thumbnail_s3_key ON media(thumbnail_s3_key);

-- Social media indexes
CREATE INDEX idx_social_accounts_tenant_id ON social_accounts(tenant_id);
CREATE INDEX idx_social_accounts_user_id ON social_accounts(user_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform);
CREATE INDEX idx_social_accounts_status ON social_accounts(status);
CREATE INDEX idx_social_accounts_content_tone ON social_accounts(content_tone);

-- Template assignment indexes
CREATE INDEX idx_newscard_templates_supports_images ON newscard_templates(supports_images);
CREATE INDEX idx_newscard_templates_is_active ON newscard_templates(is_active);
CREATE INDEX idx_newscard_templates_s3_url ON newscard_templates(s3_url);
CREATE INDEX idx_social_channel_template_assignments_tenant_id ON social_channel_template_assignments(tenant_id);
CREATE INDEX idx_social_channel_template_assignments_social_account_id ON social_channel_template_assignments(social_account_id);
CREATE INDEX idx_social_channel_template_assignments_platform ON social_channel_template_assignments(platform);

CREATE INDEX idx_social_sync_states_account_id ON social_sync_states(social_account_id);
CREATE INDEX idx_social_sync_states_tenant_id ON social_sync_states(tenant_id);
CREATE INDEX idx_social_sync_states_platform ON social_sync_states(platform);
CREATE INDEX idx_social_sync_states_sync_type ON social_sync_states(sync_type);

CREATE INDEX idx_social_media_content_account_id ON social_media_content(social_account_id);
CREATE INDEX idx_social_media_content_tenant_id ON social_media_content(tenant_id);
CREATE INDEX idx_social_media_content_platform ON social_media_content(platform);
CREATE INDEX idx_social_media_content_platform_id ON social_media_content(platform, platform_content_id);
CREATE INDEX idx_social_media_content_published_at ON social_media_content(published_at);
CREATE INDEX idx_social_media_content_processed ON social_media_content(processed);

-- Facebook cache indexes
CREATE INDEX idx_facebook_user_accounts_tenant_id ON facebook_user_accounts(tenant_id);
CREATE INDEX idx_facebook_user_accounts_facebook_user_id ON facebook_user_accounts(facebook_user_id);
CREATE INDEX idx_facebook_pages_cache_tenant_id ON facebook_pages_cache(tenant_id);
CREATE INDEX idx_facebook_pages_cache_page_id ON facebook_pages_cache(page_id);
CREATE INDEX idx_facebook_pages_cache_user_account_id ON facebook_pages_cache(facebook_user_account_id);
CREATE INDEX idx_facebook_pages_cache_last_accessed ON facebook_pages_cache(last_accessed_at);

-- Channel groups indexes
CREATE INDEX idx_channel_groups_tenant_id ON channel_groups(tenant_id);
CREATE INDEX idx_channel_groups_created_by ON channel_groups(created_by);
CREATE INDEX idx_channel_groups_is_active ON channel_groups(is_active);

-- Automation indexes
CREATE INDEX idx_cron_jobs_tenant_id ON cron_jobs(tenant_id);
CREATE INDEX idx_cron_jobs_next_run ON cron_jobs(next_run) WHERE is_enabled = true;
CREATE INDEX idx_cron_jobs_task_type ON cron_jobs(task_type);
CREATE INDEX idx_cron_job_runs_job_id ON cron_job_runs(job_id);
CREATE INDEX idx_cron_job_runs_started_at ON cron_job_runs(started_at);
CREATE INDEX idx_tenant_settings_tenant_id ON tenant_settings(tenant_id);

-- Background tasks indexes
CREATE INDEX idx_background_tasks_task_id ON background_tasks(task_id);
CREATE INDEX idx_background_tasks_tenant_id ON background_tasks(tenant_id);
CREATE INDEX idx_background_tasks_status ON background_tasks(status);
CREATE INDEX idx_background_tasks_created_at ON background_tasks(created_at);

-- Scraper jobs indexes
CREATE INDEX idx_scraper_jobs_tenant_id ON scraper_jobs(tenant_id);
CREATE INDEX idx_scraper_jobs_enabled ON scraper_jobs(is_enabled) WHERE is_enabled = true;
CREATE INDEX idx_scraper_jobs_next_run ON scraper_jobs(next_run_at) WHERE is_enabled = true;
CREATE INDEX idx_scraper_job_runs_job_id ON scraper_job_runs(scraper_job_id);
CREATE INDEX idx_scraper_job_runs_tenant_id ON scraper_job_runs(tenant_id);
CREATE INDEX idx_scraper_job_runs_status ON scraper_job_runs(status);
CREATE INDEX idx_scraper_job_social_accounts_job_id ON scraper_job_social_accounts(scraper_job_id);
CREATE INDEX idx_scraper_job_social_accounts_status ON scraper_job_social_accounts(resolution_status);
CREATE INDEX idx_scraper_job_social_accounts_platform ON scraper_job_social_accounts(platform);

-- Pipeline indexes
CREATE INDEX idx_pipelines_tenant_id ON pipelines(tenant_id);
CREATE INDEX idx_pipelines_created_by ON pipelines(created_by);
CREATE INDEX idx_pipelines_status ON pipelines(status);
CREATE INDEX idx_pipelines_last_run ON pipelines(last_run);

CREATE INDEX idx_news_items_pipeline_id ON news_items(pipeline_id);
CREATE INDEX idx_news_items_moderation_status ON news_items(moderation_status);
CREATE INDEX idx_news_items_fetched_at ON news_items(fetched_at);
CREATE INDEX idx_news_items_source ON news_items(source);

create index IF not exists idx_news_items_is_approved on public.news_items using btree (is_approved) TABLESPACE pg_default;
create index IF not exists idx_news_items_status on public.news_items using btree (status) TABLESPACE pg_default;

CREATE INDEX idx_pipeline_runs_pipeline_id ON pipeline_runs(pipeline_id);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_started_at ON pipeline_runs(started_at);

-- Supporting table indexes
CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id);

CREATE INDEX idx_invitations_tenant_id ON invitations(tenant_id);
CREATE INDEX idx_invitations_email ON invitations(email);
CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_status ON invitations(status);

CREATE INDEX idx_workflows_tenant_id ON workflows(tenant_id);
CREATE INDEX idx_workflows_is_active ON workflows(is_active);

CREATE INDEX idx_webhooks_tenant_id ON webhooks(tenant_id);
CREATE INDEX idx_webhooks_is_active ON webhooks(is_active);

-- Analytics indexes
CREATE INDEX idx_post_analytics_tenant_id ON post_analytics(tenant_id);
CREATE INDEX idx_post_analytics_post_id ON post_analytics(post_id);
CREATE INDEX idx_post_analytics_platform ON post_analytics(platform);
CREATE INDEX idx_post_analytics_collected_at ON post_analytics(collected_at);

CREATE INDEX idx_usage_tracking_tenant_id ON usage_tracking(tenant_id);
CREATE INDEX idx_usage_tracking_user_id ON usage_tracking(user_id);
CREATE INDEX idx_usage_tracking_created_at ON usage_tracking(created_at);

-- LLM logs indexes
CREATE INDEX idx_llm_logs_tenant_id ON llm_logs(tenant_id);
CREATE INDEX idx_llm_logs_created_at ON llm_logs(created_at DESC);
CREATE INDEX idx_llm_logs_profile ON llm_logs(profile);
CREATE INDEX idx_llm_logs_model ON llm_logs(model);
CREATE INDEX idx_llm_logs_status ON llm_logs(status);
CREATE INDEX idx_llm_logs_service_name ON llm_logs(service_name);
CREATE INDEX idx_llm_logs_tenant_created ON llm_logs(tenant_id, created_at DESC);

CREATE INDEX idx_content_adaptations_post_id ON content_adaptations(post_id);
CREATE INDEX idx_content_adaptations_channel_id ON content_adaptations(channel_id);
CREATE INDEX idx_content_adaptations_tenant_id ON content_adaptations(tenant_id);
CREATE INDEX idx_content_adaptations_success ON content_adaptations(success);
CREATE INDEX idx_content_adaptations_created_at ON content_adaptations(created_at);

-- Post drafts indexes
CREATE INDEX idx_post_drafts_tenant_id ON post_drafts(tenant_id);
CREATE INDEX idx_post_drafts_user_id ON post_drafts(user_id);
CREATE INDEX idx_post_drafts_status ON post_drafts(status);
CREATE INDEX idx_post_drafts_external_news_id ON post_drafts(external_news_id);
CREATE INDEX idx_post_drafts_post_id ON post_drafts(post_id);
CREATE INDEX idx_post_drafts_social_account_id ON post_drafts(social_account_id);
CREATE INDEX idx_post_drafts_created_at ON post_drafts(created_at DESC);
CREATE INDEX idx_post_drafts_status_created ON post_drafts(status, created_at DESC);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to all relevant tables
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_accounts_updated_at BEFORE UPDATE ON social_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_newscard_templates_updated_at BEFORE UPDATE ON newscard_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_channel_template_assignments_updated_at BEFORE UPDATE ON social_channel_template_assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_sync_states_updated_at BEFORE UPDATE ON social_sync_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_social_media_content_updated_at BEFORE UPDATE ON social_media_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_user_accounts_updated_at 
    BEFORE UPDATE ON facebook_user_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_facebook_pages_cache_updated_at 
    BEFORE UPDATE ON facebook_pages_cache 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channel_groups_updated_at BEFORE UPDATE ON channel_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cron_jobs_updated_at 
    BEFORE UPDATE ON cron_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_settings_updated_at 
    BEFORE UPDATE ON tenant_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipelines_updated_at BEFORE UPDATE ON pipelines
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invitations_updated_at BEFORE UPDATE ON invitations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhooks_updated_at BEFORE UPDATE ON webhooks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scraper_jobs_updated_at BEFORE UPDATE ON scraper_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_adaptations_updated_at BEFORE UPDATE ON content_adaptations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- RLS TENANT CONTEXT FUNCTION
-- =====================================================

-- Helper function to safely get the current tenant ID for RLS policies
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    tenant_id_text TEXT;
BEGIN
    -- Get the current tenant ID setting
    tenant_id_text := current_setting('app.current_tenant_id', true);

    -- Return NULL if not set or empty, otherwise cast to UUID
    IF tenant_id_text IS NULL OR tenant_id_text = '' THEN
        RETURN NULL;
    ELSE
        RETURN tenant_id_text::UUID;
    END IF;
END;
$$;

-- Create a wrapper function for set_config that can be called via RPC
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_id_param UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Set the tenant context for RLS policies
    PERFORM set_config('app.current_tenant_id', tenant_id_param::text, true);
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO authenticated;
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO anon;
GRANT EXECUTE ON FUNCTION set_tenant_context(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION set_tenant_context(UUID) TO anon;

COMMENT ON FUNCTION get_current_tenant_id() IS 'Safely retrieves the current tenant ID from session settings for RLS policies';
COMMENT ON FUNCTION set_tenant_context(UUID) IS 'Sets the tenant context for Row Level Security policies';

-- =====================================================
-- FACEBOOK CACHE FUNCTIONS
-- =====================================================

-- Function to clean up expired Facebook tokens
CREATE OR REPLACE FUNCTION cleanup_expired_facebook_tokens()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER := 0;
    temp_count INTEGER := 0;
BEGIN
    -- Clean up expired user tokens
    DELETE FROM facebook_user_accounts 
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Clean up pages with expired tokens
    DELETE FROM facebook_pages_cache 
    WHERE access_token_expires_at IS NOT NULL AND access_token_expires_at < NOW();
    
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    RETURN deleted_count;
END;
$$;

-- Function to update last accessed time for Facebook pages
CREATE OR REPLACE FUNCTION update_facebook_page_last_accessed(
    p_tenant_id UUID,
    p_page_id TEXT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE facebook_pages_cache 
    SET last_accessed_at = NOW(),
        updated_at = NOW()
    WHERE tenant_id = p_tenant_id 
    AND page_id = p_page_id;
END;
$$;

-- =====================================================
-- SCRAPER JOBS FUNCTIONS
-- =====================================================

-- Function to update next_run_at based on cron schedule
CREATE OR REPLACE FUNCTION update_scraper_job_next_run()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate next run time based on cron schedule
    -- This is a simplified implementation - in production you'd use a proper cron parser
    IF NEW.schedule_cron = '*/1 * * * *' THEN
        NEW.next_run_at = NOW() + INTERVAL '1 minute';
    ELSIF NEW.schedule_cron = '*/5 * * * *' THEN
        NEW.next_run_at = NOW() + INTERVAL '5 minutes';
    ELSIF NEW.schedule_cron = '*/15 * * * *' THEN
        NEW.next_run_at = NOW() + INTERVAL '15 minutes';
    ELSIF NEW.schedule_cron = '0 * * * *' THEN
        NEW.next_run_at = DATE_TRUNC('hour', NOW()) + INTERVAL '1 hour';
    ELSIF NEW.schedule_cron = '0 */6 * * *' THEN
        NEW.next_run_at = DATE_TRUNC('hour', NOW()) + INTERVAL '6 hours';
    ELSIF NEW.schedule_cron = '0 0 * * *' THEN
        NEW.next_run_at = DATE_TRUNC('day', NOW()) + INTERVAL '1 day';
    ELSE
        -- Default to 5 minutes for unknown patterns
        NEW.next_run_at = NOW() + INTERVAL '5 minutes';
    END IF;

    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update next_run_at
CREATE TRIGGER trigger_update_scraper_job_next_run
    BEFORE INSERT OR UPDATE ON scraper_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_scraper_job_next_run();

-- Function to increment job counters after run completion
CREATE OR REPLACE FUNCTION increment_scraper_job_counters(
    job_id UUID,
    success BOOLEAN,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    error_msg TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE scraper_jobs SET
        run_count = run_count + 1,
        success_count = CASE WHEN success THEN success_count + 1 ELSE success_count END,
        error_count = CASE WHEN NOT success THEN error_count + 1 ELSE error_count END,
        last_run_at = last_run,
        next_run_at = next_run,
        last_error = CASE WHEN NOT success THEN error_msg ELSE NULL END,
        updated_at = NOW()
    WHERE id = job_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- ROW LEVEL SECURITY (ENABLED)
-- =====================================================

-- Enable RLS on all tenant-scoped tables for database-level security enforcement
-- This provides defense-in-depth protection by enforcing tenant isolation at the database layer
-- in addition to application-level filtering

-- Core tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Content tables
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE media ENABLE ROW LEVEL SECURITY;

-- Social media tables
ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_sync_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_media_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE newscard_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_channel_template_assignments ENABLE ROW LEVEL SECURITY;

-- Facebook cache tables
ALTER TABLE facebook_user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE facebook_pages_cache ENABLE ROW LEVEL SECURITY;

-- Channel groups
ALTER TABLE channel_groups ENABLE ROW LEVEL SECURITY;

-- Automation tables
ALTER TABLE cron_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cron_job_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_tasks ENABLE ROW LEVEL SECURITY;

-- Pipeline tables
ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_job_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_job_social_accounts ENABLE ROW LEVEL SECURITY;

-- Supporting tables
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;

-- Analytics tables
ALTER TABLE post_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- Content adaptations
ALTER TABLE content_adaptations ENABLE ROW LEVEL SECURITY;

-- Post drafts
ALTER TABLE post_drafts ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS POLICIES
-- =====================================================

-- Tenants: Users can only see their own tenant
CREATE POLICY tenants_isolation ON tenants
    FOR ALL
    USING (id = get_current_tenant_id())
    WITH CHECK (id = get_current_tenant_id());

-- Users: Scoped to tenant
CREATE POLICY users_tenant_isolation ON users
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Posts: Scoped to tenant
CREATE POLICY posts_tenant_isolation ON posts
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Media: Scoped to tenant
CREATE POLICY media_tenant_isolation ON media
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Social accounts: Scoped to tenant
CREATE POLICY social_accounts_tenant_isolation ON social_accounts
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Social sync states: Scoped to tenant
CREATE POLICY social_sync_states_tenant_isolation ON social_sync_states
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Social media content: Scoped to tenant
CREATE POLICY social_media_content_tenant_isolation ON social_media_content
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Newscard templates: Global access (not tenant-scoped)
CREATE POLICY newscard_templates_all_access ON newscard_templates
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Social channel template assignments: Scoped to tenant
CREATE POLICY social_channel_template_assignments_tenant_isolation ON social_channel_template_assignments
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Facebook user accounts: Scoped to tenant
CREATE POLICY facebook_user_accounts_tenant_isolation ON facebook_user_accounts
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Facebook pages cache: Scoped to tenant
CREATE POLICY facebook_pages_cache_tenant_isolation ON facebook_pages_cache
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Channel groups: Scoped to tenant
CREATE POLICY channel_groups_tenant_isolation ON channel_groups
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Cron jobs: Scoped to tenant (NULL tenant_id means system-wide)
CREATE POLICY cron_jobs_tenant_isolation ON cron_jobs
    FOR ALL
    USING (tenant_id IS NULL OR tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id IS NULL OR tenant_id = get_current_tenant_id());

-- Cron job runs: Scoped via parent cron_jobs table
CREATE POLICY cron_job_runs_tenant_isolation ON cron_job_runs
    FOR ALL
    USING (
        job_id IN (
            SELECT id FROM cron_jobs
            WHERE tenant_id IS NULL OR tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        job_id IN (
            SELECT id FROM cron_jobs
            WHERE tenant_id IS NULL OR tenant_id = get_current_tenant_id()
        )
    );

-- Tenant settings: Scoped to tenant
CREATE POLICY tenant_settings_tenant_isolation ON tenant_settings
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Background tasks: Scoped to tenant
CREATE POLICY background_tasks_tenant_isolation ON background_tasks
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Pipelines: Scoped to tenant
CREATE POLICY pipelines_tenant_isolation ON pipelines
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- News items: Scoped via parent pipelines table or direct tenant_id
CREATE POLICY news_items_tenant_isolation ON news_items
    FOR ALL
    USING (
        tenant_id = get_current_tenant_id() OR
        pipeline_id IN (
            SELECT id FROM pipelines
            WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        tenant_id = get_current_tenant_id() OR
        pipeline_id IN (
            SELECT id FROM pipelines
            WHERE tenant_id = get_current_tenant_id()
        )
    );

-- Pipeline runs: Scoped via parent pipelines table
CREATE POLICY pipeline_runs_tenant_isolation ON pipeline_runs
    FOR ALL
    USING (
        pipeline_id IN (
            SELECT id FROM pipelines
            WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        pipeline_id IN (
            SELECT id FROM pipelines
            WHERE tenant_id = get_current_tenant_id()
        )
    );

-- Scraper jobs: Scoped to tenant
CREATE POLICY scraper_jobs_tenant_isolation ON scraper_jobs
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Scraper job runs: Scoped to tenant
CREATE POLICY scraper_job_runs_tenant_isolation ON scraper_job_runs
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Scraper job social accounts: Scoped to tenant via scraper_jobs
CREATE POLICY scraper_job_social_accounts_tenant_isolation ON scraper_job_social_accounts
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM scraper_jobs
            WHERE scraper_jobs.id = scraper_job_social_accounts.scraper_job_id
            AND scraper_jobs.tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM scraper_jobs
            WHERE scraper_jobs.id = scraper_job_social_accounts.scraper_job_id
            AND scraper_jobs.tenant_id = get_current_tenant_id()
        )
    );

-- Subscriptions: Scoped to tenant
CREATE POLICY subscriptions_tenant_isolation ON subscriptions
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Invitations: Scoped to tenant
CREATE POLICY invitations_tenant_isolation ON invitations
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Workflows: Scoped to tenant
CREATE POLICY workflows_tenant_isolation ON workflows
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Webhooks: Scoped to tenant
CREATE POLICY webhooks_tenant_isolation ON webhooks
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Post analytics: Scoped to tenant
CREATE POLICY post_analytics_tenant_isolation ON post_analytics
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Usage tracking: Scoped to tenant
CREATE POLICY usage_tracking_tenant_isolation ON usage_tracking
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- LLM logs: Tenant isolation with service role access
ALTER TABLE llm_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY llm_logs_tenant_isolation ON llm_logs
    FOR SELECT
    USING (
        tenant_id IN (
            SELECT tenant_id FROM users WHERE id = auth.uid()
        )
    );

CREATE POLICY llm_logs_service_role ON llm_logs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Content adaptations: Scoped to tenant
CREATE POLICY content_adaptations_tenant_isolation ON content_adaptations
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Post drafts: Scoped to tenant
CREATE POLICY post_drafts_tenant_isolation ON post_drafts
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- =====================================================
-- VIEWS FOR ANALYTICS
-- =====================================================

-- LLM usage statistics view
CREATE OR REPLACE VIEW llm_usage_stats AS
SELECT
    tenant_id,
    profile,
    model,
    service_name,
    DATE(created_at) as date,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens_used,
    SUM(prompt_tokens) as total_prompt_tokens,
    SUM(completion_tokens) as total_completion_tokens,
    AVG(execution_time_ms) as avg_execution_time_ms,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count
FROM llm_logs
GROUP BY tenant_id, profile, model, service_name, DATE(created_at);

COMMENT ON VIEW llm_usage_stats IS 'Daily aggregated statistics for LLM usage by tenant, profile, and service';

-- =====================================================
-- DATA INITIALIZATION
-- =====================================================

-- Initialize tenant settings for existing tenants
INSERT INTO tenant_settings (tenant_id, news_automation, created_at)
SELECT 
    id as tenant_id,
    jsonb_build_object(
        'enabled', false,
        'auto_publish', false,
        'categories', jsonb_build_array('technology'),
        'max_articles_per_run', 5,
        'schedule', '0 */2 * * *'
    ) as news_automation,
    NOW() as created_at
FROM tenants
ON CONFLICT (tenant_id) DO NOTHING;

-- Update existing media records with size column default values
UPDATE media 
SET size = COALESCE(file_size, 1024000)
WHERE size IS NULL;

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE tenants IS 'Multi-tenant workspace information with subscription management';
COMMENT ON TABLE users IS 'User accounts with tenant association and role-based permissions';
COMMENT ON TABLE posts IS 'Social media content posts with multi-platform publishing support';
COMMENT ON TABLE media IS 'Media library with tenant isolation and AI generation support';
COMMENT ON TABLE social_accounts IS 'Connected social media accounts with token management and content customization options';
COMMENT ON TABLE llm_logs IS 'Logs all LLM API calls for observability, debugging, and analytics';
COMMENT ON COLUMN llm_logs.profile IS 'LLM profile used: DEFAULT, PRECISE, CREATIVE, or ANALYTICAL';
COMMENT ON COLUMN llm_logs.operation IS 'Type of operation: generate, stream, or batch_generate';
COMMENT ON COLUMN llm_logs.messages IS 'Full message history sent to LLM';
COMMENT ON COLUMN llm_logs.response_content IS 'Generated text response from LLM';
COMMENT ON COLUMN llm_logs.execution_time_ms IS 'Time taken to complete the LLM request in milliseconds';
COMMENT ON COLUMN llm_logs.service_name IS 'Service that initiated the LLM call (e.g., ai_content_service)';
COMMENT ON TABLE social_sync_states IS 'Tracks sync state and cursors for social media accounts';
COMMENT ON TABLE social_media_content IS 'Stores fetched social media content with deduplication';
COMMENT ON TABLE facebook_user_accounts IS 'Cached Facebook user account information with access tokens per tenant - RLS enabled for database-level tenant isolation';
COMMENT ON TABLE facebook_pages_cache IS 'Cached Facebook pages information with page access tokens per tenant - RLS enabled for database-level tenant isolation';
COMMENT ON TABLE channel_groups IS 'Organized groups of social media channels for bulk operations';
COMMENT ON TABLE cron_jobs IS 'Stores scheduled automation jobs for tenants';
COMMENT ON TABLE cron_job_runs IS 'Tracks execution history of cron jobs';
COMMENT ON TABLE tenant_settings IS 'Stores tenant-specific automation and feature settings';
COMMENT ON TABLE background_tasks IS 'Background task tracking and management';
COMMENT ON TABLE pipelines IS 'Content processing pipelines for automated content workflow';
COMMENT ON TABLE news_items IS 'Content fetched and processed by pipelines with moderation support';
COMMENT ON TABLE pipeline_runs IS 'Tracks pipeline execution history and performance metrics';
COMMENT ON TABLE scraper_jobs IS 'Social media scraper jobs configuration for automated content discovery';
COMMENT ON TABLE scraper_job_runs IS 'Tracks execution history and results of scraper jobs';
COMMENT ON TABLE subscriptions IS 'Stripe subscription management and billing information';
COMMENT ON TABLE invitations IS 'User invitations to tenant workspaces';
COMMENT ON TABLE workflows IS 'Configurable content approval workflows';
COMMENT ON TABLE webhooks IS 'External webhook configurations for platform integrations';
COMMENT ON TABLE post_analytics IS 'Analytics data aggregated from social platforms';
COMMENT ON TABLE usage_tracking IS 'API usage tracking for subscription tier enforcement';
COMMENT ON TABLE content_adaptations IS 'Tracks content adaptation results for analytics and debugging';
COMMENT ON TABLE post_drafts IS 'Stores LLM-generated content adaptations for human review before publishing. Supports both external news and regular posts';
COMMENT ON COLUMN post_drafts.external_news_id IS 'Link to external_news_items if this draft is from News Items module';
COMMENT ON COLUMN post_drafts.post_id IS 'Link to posts if this draft is from Post Creator module';
COMMENT ON COLUMN post_drafts.generated_content IS 'Original LLM-generated content (immutable)';
COMMENT ON COLUMN post_drafts.final_content IS 'User-edited content to be published (editable)';
COMMENT ON COLUMN post_drafts.status IS 'Workflow status: PENDING_REVIEW → APPROVED → PUBLISHED or REJECTED';
COMMENT ON COLUMN post_drafts.publish_result IS 'Result from social media API after publishing';

-- Key column documentation
COMMENT ON COLUMN posts.content IS 'JSONB structure containing post text and media references';
COMMENT ON COLUMN posts.channels IS 'JSONB array of platform-specific configurations and customizations';
COMMENT ON COLUMN posts.metadata IS 'Additional metadata for posts, including automation source information';
COMMENT ON COLUMN posts.news_card_url IS 'URL to generated news card image for the post';
COMMENT ON COLUMN posts.preview_html IS 'Generated HTML preview of the post content';
COMMENT ON COLUMN posts.publish_results IS 'JSON structure storing publishing results from background tasks, including platform-specific responses and errors';
COMMENT ON COLUMN posts.processing_task_id IS 'ID of the background task currently processing this post';
COMMENT ON COLUMN posts.error_message IS 'Error message if post processing failed';
COMMENT ON COLUMN posts.keywords IS 'AI-generated keywords extracted from post content';
COMMENT ON COLUMN posts.image_search_caption IS 'AI-generated search term for finding relevant stock photos or AI-generated images';
COMMENT ON COLUMN media.size IS 'File size in bytes';
COMMENT ON COLUMN cron_jobs.schedule IS 'Cron expression defining when the job should run';
COMMENT ON COLUMN cron_jobs.task_type IS 'Type of automation task: news_fetch, scheduled_posts, analytics_sync';
COMMENT ON COLUMN cron_jobs.parameters IS 'Job-specific parameters and configuration';
COMMENT ON COLUMN social_sync_states.last_cursor IS 'Platform-specific cursor for pagination';
COMMENT ON COLUMN social_sync_states.last_item_id IS 'ID of the last item synced to prevent duplicates';
COMMENT ON COLUMN social_sync_states.sync_config IS 'Platform-specific sync configuration (query terms, filters, etc.)';
COMMENT ON COLUMN social_media_content.platform_content_id IS 'Original platform content ID for deduplication';
COMMENT ON COLUMN social_media_content.content_data IS 'Full content data from platform API';
COMMENT ON COLUMN social_media_content.processed IS 'Whether content has been processed for moderation/analysis';
COMMENT ON COLUMN facebook_user_accounts.expires_at IS 'When the user access token expires (NULL for non-expiring tokens)';
COMMENT ON COLUMN facebook_pages_cache.access_token_expires_at IS 'When the page access token expires (NULL for non-expiring tokens)';
COMMENT ON COLUMN facebook_pages_cache.last_accessed_at IS 'Last time this page was accessed for publishing or API calls';
COMMENT ON COLUMN social_accounts.content_tone IS 'Content tone/style for this social channel (e.g., professional, casual, friendly, formal)';
COMMENT ON COLUMN social_accounts.custom_instructions IS 'Custom AI prompt instructions specific to this social channel for content generation and customization';
COMMENT ON COLUMN social_accounts.auto_image_search IS 'Enable automatic image search and attachment when publishing posts based on image_search_caption';
COMMENT ON COLUMN background_tasks.task_id IS 'Unique identifier for the background task';
COMMENT ON COLUMN background_tasks.task_type IS 'Type of background task (e.g., publish_post, generate_newscard)';
COMMENT ON COLUMN background_tasks.status IS 'Current status of the task (pending, processing, completed, failed)';
COMMENT ON COLUMN background_tasks.data IS 'Input data for the task';
COMMENT ON COLUMN background_tasks.result IS 'Result data from the completed task';
COMMENT ON COLUMN background_tasks.progress IS 'Progress tracking information';
COMMENT ON COLUMN scraper_jobs.post_approval_logic IS 'Natural language description of approval/rejection logic for posts. If null, default moderation logic is used.';

-- =====================================================
-- DEFAULT DATA INSERTION
-- =====================================================

-- Insert default newscard templates
INSERT INTO newscard_templates (template_name, template_display_name, template_path, supports_images, description) VALUES
-- Templates without images
('template_1_modern_gradient', 'Modern Gradient', '/templates/newscard/template_1_modern_gradient.html', false, 'Modern gradient background design'),
('template_2_dark_tech', 'Dark Tech', '/templates/newscard/template_2_dark_tech.html', false, 'Dark theme with tech styling'),
('template_3_clean_minimal', 'Clean Minimal', '/templates/newscard/template_3_clean_minimal.html', false, 'Clean and minimal design'),
('template_4_newspaper', 'Newspaper', '/templates/newscard/template_4_newspaper.html', false, 'Traditional newspaper style'),
('template_5_magazine', 'Magazine', '/templates/newscard/template_5_magazine.html', false, 'Magazine-style layout'),
('template_6_corporate', 'Corporate', '/templates/newscard/template_6_corporate.html', false, 'Professional corporate design'),

-- Templates with images
('template_1_modern_card_with_image', 'Modern Card with Image', '/templates/newscard/with_images/template_1_modern_card.html', true, 'Modern card design with image support'),
('template_2_side_by_side_with_image', 'Side by Side with Image', '/templates/newscard/with_images/template_2_side_by_side.html', true, 'Side-by-side layout with image'),
('template_3_magazine_overlay_with_image', 'Magazine Overlay with Image', '/templates/newscard/with_images/template_3_magazine_overlay.html', true, 'Magazine style with image overlay'),
('template_4_minimal_circular_with_image', 'Minimal Circular with Image', '/templates/newscard/with_images/template_4_minimal_circular.html', true, 'Minimal design with circular image'),
('template_5_news_bulletin_with_image', 'News Bulletin with Image', '/templates/newscard/with_images/template_5_news_bulletin.html', true, 'News bulletin style with image'),

-- Newscard Nue templates without images
('left_content_right_image_without_image', 'Left Content Right Image (No Image)', '/templates/newscard_nue/without_images/left_content_right_image.html', false, 'Left content, right image layout for content without images'),
('vertical_image_without_image', 'Vertical Image (No Image)', '/templates/newscard_nue/without_images/vertical_image.html', false, 'Vertical layout optimized for content without images'),
('news-card-hero-left-stack_without_image', 'News Card Hero Left Stack (No Image)', '/templates/newscard_nue/without_images/news-card-hero-left-stack.html', false, 'Hero layout with left-stacked content for content without images'),
('full_bleed_image_without_image', 'Full Bleed Image (No Image)', '/templates/newscard_nue/without_images/full_bleed_image.html', false, 'Full bleed layout with drawer design for content without images'),
('horizontal_image_without_image', 'Horizontal Image (No Image)', '/templates/newscard_nue/without_images/horizontal_image.html', false, 'Horizontal layout optimized for content without images'),
('top_bar_with_logo_without_image', 'Top Bar with Logo (No Image)', '/templates/newscard_nue/without_images/top_bar_with_logo.html', false, 'Top bar layout with logo for content without images'),

-- Newscard Nue templates with images
('left_content_right_image_with_image', 'Left Content Right Image (With Image)', '/templates/newscard_nue/with_images/left_content_right_image.html', true, 'Left content, right image layout supporting images'),
('vertical_image_with_image', 'Vertical Image (With Image)', '/templates/newscard_nue/with_images/vertical_image.html', true, 'Vertical layout optimized for content with images'),
('news-card-hero-left-stack_with_image', 'News Card Hero Left Stack (With Image)', '/templates/newscard_nue/with_images/news-card-hero-left-stack.html', true, 'Hero layout with left-stacked content supporting images'),
('full_bleed_image_with_image', 'Full Bleed Image (With Image)', '/templates/newscard_nue/with_images/full_bleed_image.html', true, 'Full bleed layout with drawer design supporting images'),
('horizontal_image_with_image', 'Horizontal Image (With Image)', '/templates/newscard_nue/with_images/horizontal_image.html', true, 'Horizontal layout optimized for content with images'),
('top_bar_with_logo_with_image', 'Top Bar with Logo (With Image)', '/templates/newscard_nue/with_images/top_bar_with_logo.html', true, 'Top bar layout with logo supporting images')
ON CONFLICT (template_name) DO UPDATE SET
    template_display_name = EXCLUDED.template_display_name,
    template_path = EXCLUDED.template_path,
    supports_images = EXCLUDED.supports_images,
    description = EXCLUDED.description,
    updated_at = NOW();



-- Comments for new tables
COMMENT ON TABLE newscard_templates IS 'Master table of available newscard templates with metadata';
COMMENT ON TABLE social_channel_template_assignments IS 'Stores template assignments for each social channel, allowing different templates for content with and without images';
COMMENT ON COLUMN social_channel_template_assignments.template_with_image IS 'Template to use when content includes images';
COMMENT ON COLUMN social_channel_template_assignments.template_without_image IS 'Template to use when content has no images';
COMMENT ON COLUMN newscard_templates.supports_images IS 'Whether this template supports displaying images';
-- =====================================================
-- External News System
-- =====================================================
-- Generic system for ingesting, approving, and publishing external news
-- Supports NewsIt and other future external sources
-- Includes approval workflow and multi-channel-group publishing
-- Created: 2025-01-29

-- TABLE: external_news_items
-- Generic storage for news from external sources (NewsIt, RSS feeds, etc.)

CREATE TABLE IF NOT EXISTS external_news_items (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- External source tracking
    external_source VARCHAR(50) NOT NULL,  -- 'newsit', 'rss', 'custom', etc.
    external_id VARCHAR(255) NOT NULL,     -- Source's unique ID (e.g., NewsIt news_id)
    sqs_message_id VARCHAR(255),           -- For deduplication from SQS

    -- Pipeline relationship (for pipeline-sourced content)
    pipeline_id UUID REFERENCES pipelines(id) ON DELETE CASCADE,

    -- Core content (supports multilingual via JSONB)
    title VARCHAR(500) NOT NULL,           -- Default/primary language title
    content TEXT NOT NULL,                 -- Default/primary content
    processed_content TEXT,                -- AI-processed/cleaned version of original content
    multilingual_data JSONB,               -- Full multilingual structure: { "en": {...}, "ta": {...} }

    -- Metadata
    category VARCHAR(100),
    category_data JSONB,                   -- Multilingual category info
    city_data JSONB,                       -- City/district info with multilingual names
    topics JSONB,                          -- Array of topics with multilingual data
    tags TEXT[],

    -- Media
    images JSONB,                          -- All image variants: { "original_url": "...", "thumbnail_url": "...", "low_res_url": "..." }
    generated_image_url VARCHAR(500),      -- URL to AI-generated or fetched image for this news item
    media_urls TEXT[],                     -- Additional media if any

    -- Source information
    source_url TEXT,
    source_name VARCHAR(255),

    -- Flags
    is_breaking BOOLEAN DEFAULT FALSE,

    -- Publishing tracking
    published_channels TEXT[],             -- Array of channel IDs where this news item has been published
    published_at TIMESTAMP WITH TIME ZONE, -- When the source originally published this article (not when we published to social media)

    -- AI Moderation (separate from manual approval)
    moderation_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    moderation_score DECIMAL(3,2),         -- AI moderation confidence score (0.00 to 1.00)
    moderation_flags TEXT[],               -- AI-detected content flags (e.g., spam, nsfw, low-quality)

    -- Approval workflow (manual review)
    approval_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Legacy compatibility fields (for transition period)
    status VARCHAR(100),                   -- Legacy status field for backward compatibility
    is_approved BOOLEAN DEFAULT FALSE,     -- Legacy approval flag for backward compatibility

    -- Timestamps
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    moderation_reason TEXT,
    moderated_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT unique_external_news UNIQUE(external_source, external_id, tenant_id),
    CONSTRAINT unique_sqs_message UNIQUE(sqs_message_id) WHERE sqs_message_id IS NOT NULL,
    CONSTRAINT valid_approval_status CHECK (approval_status IN ('pending', 'approved', 'rejected'))
);

-- Indexes for external_news_items
CREATE INDEX idx_external_news_tenant_id ON external_news_items(tenant_id);
CREATE INDEX idx_external_news_approval_status ON external_news_items(approval_status);
CREATE INDEX idx_external_news_external_source ON external_news_items(external_source);
CREATE INDEX idx_external_news_external_id ON external_news_items(external_source, external_id);
CREATE INDEX idx_external_news_fetched_at ON external_news_items(fetched_at DESC);
CREATE INDEX idx_external_news_is_breaking ON external_news_items(is_breaking) WHERE is_breaking = TRUE;
CREATE INDEX idx_external_news_created_at ON external_news_items(created_at DESC);
CREATE INDEX idx_external_news_city_data ON external_news_items USING GIN (city_data);

-- Indexes for migration-added columns
CREATE INDEX idx_external_news_pipeline_id ON external_news_items(pipeline_id) WHERE pipeline_id IS NOT NULL;
CREATE INDEX idx_external_news_moderation_status ON external_news_items(moderation_status);
CREATE INDEX idx_external_news_status ON external_news_items(status) WHERE status IS NOT NULL;
CREATE INDEX idx_external_news_is_approved ON external_news_items(is_approved);
CREATE INDEX idx_external_news_tenant_source_status ON external_news_items(tenant_id, external_source, approval_status);
CREATE INDEX idx_external_news_published_channels ON external_news_items USING GIN(published_channels) WHERE published_channels IS NOT NULL;

-- TABLE: external_news_publications
-- Track publishing history to channel groups with status

CREATE TABLE IF NOT EXISTS external_news_publications (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_news_id UUID NOT NULL REFERENCES external_news_items(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Publishing target
    channel_group_id UUID NOT NULL REFERENCES channel_groups(id) ON DELETE CASCADE,

    -- Post created for this publication
    post_id UUID REFERENCES posts(id) ON DELETE SET NULL,

    -- Publishing status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'publishing', 'published', 'failed'

    -- Publishing metadata
    initiated_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    initiated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Results
    publish_results JSONB,                 -- Per-channel results: { "facebook": { "success": true, ... }, ... }
    error_message TEXT,

    -- Content customization (if any)
    customized_title VARCHAR(500),
    customized_content TEXT,
    selected_language VARCHAR(10),         -- Which language was used: 'en', 'ta', etc.

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_publication_status CHECK (status IN ('pending', 'publishing', 'published', 'failed'))
);

-- Indexes for external_news_publications
CREATE INDEX idx_external_news_pub_news_id ON external_news_publications(external_news_id);
CREATE INDEX idx_external_news_pub_tenant_id ON external_news_publications(tenant_id);
CREATE INDEX idx_external_news_pub_channel_group ON external_news_publications(channel_group_id);
CREATE INDEX idx_external_news_pub_status ON external_news_publications(status);
CREATE INDEX idx_external_news_pub_post_id ON external_news_publications(post_id);
CREATE INDEX idx_external_news_pub_initiated_at ON external_news_publications(initiated_at DESC);

-- Enable RLS
ALTER TABLE external_news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_news_publications ENABLE ROW LEVEL SECURITY;

-- RLS Policies for external_news_items
CREATE POLICY external_news_items_tenant_isolation ON external_news_items
    FOR ALL
    USING (
        -- Direct tenant access
        tenant_id = get_current_tenant_id()
        OR
        -- Indirect access via pipeline (for pipeline-sourced content)
        pipeline_id IN (
            SELECT id FROM pipelines WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        -- Direct tenant write
        tenant_id = get_current_tenant_id()
        OR
        -- Pipeline write (for automation)
        pipeline_id IN (
            SELECT id FROM pipelines WHERE tenant_id = get_current_tenant_id()
        )
    );

-- RLS Policies for external_news_publications
CREATE POLICY external_news_pub_tenant_isolation ON external_news_publications
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Table and column comments
COMMENT ON TABLE external_news_items IS 'Generic storage for news from external sources (NewsIt, RSS, pipelines, etc.) with approval workflow and multilingual support';
COMMENT ON TABLE external_news_publications IS 'Tracks publishing history of external news to channel groups with status and results';
COMMENT ON COLUMN external_news_items.external_source IS 'Source system identifier: newsit, rss, pipeline, slack, facebook, twitter, custom, etc.';
COMMENT ON COLUMN external_news_items.external_id IS 'Unique ID from the external source system';
COMMENT ON COLUMN external_news_items.sqs_message_id IS 'SQS message ID for deduplication';
COMMENT ON COLUMN external_news_items.pipeline_id IS 'Optional reference to pipeline for pipeline-sourced content. NULL for NewsIt/Slack/manual entries.';
COMMENT ON COLUMN external_news_items.processed_content IS 'AI-processed/cleaned version of original content';
COMMENT ON COLUMN external_news_items.generated_image_url IS 'URL to AI-generated or fetched image for this news item';
COMMENT ON COLUMN external_news_items.published_channels IS 'Array of channel IDs where this news item has been published. Tracks multi-channel publishing.';
COMMENT ON COLUMN external_news_items.published_at IS 'When the source originally published this article (not when we published to social media). Important for sorting and analytics.';
COMMENT ON COLUMN external_news_items.moderation_status IS 'AI moderation status: pending, approved, rejected. Separate from manual approval_status.';
COMMENT ON COLUMN external_news_items.moderation_score IS 'AI moderation confidence score (0.00 to 1.00). Higher = more confident.';
COMMENT ON COLUMN external_news_items.moderation_flags IS 'AI-detected content flags (e.g., spam, nsfw, low-quality)';
COMMENT ON COLUMN external_news_items.status IS 'Legacy status field for backward compatibility. Use approval_status going forward.';
COMMENT ON COLUMN external_news_items.is_approved IS 'Legacy approval flag for backward compatibility. Use approval_status going forward.';
COMMENT ON COLUMN external_news_items.multilingual_data IS 'Full multilingual content structure as JSONB';
COMMENT ON COLUMN external_news_items.city_data IS 'City/district information with multilingual names';
COMMENT ON COLUMN external_news_items.images IS 'Image URLs: original_url, thumbnail_url, low_res_url';
COMMENT ON COLUMN external_news_items.approval_status IS 'Manual approval workflow status: pending, approved, rejected';
COMMENT ON COLUMN external_news_publications.status IS 'Publishing status: pending, publishing, published, failed';
COMMENT ON COLUMN external_news_publications.publish_results IS 'Per-channel publishing results as JSONB';
COMMENT ON COLUMN external_news_publications.selected_language IS 'Language variant used for publishing';

-- =====================================================
-- SCHEMA CREATION COMPLETE
-- =====================================================

-- The consolidated OmniPush schema is now ready for use
-- This schema includes all features:
-- - Multi-tenant architecture with strict data isolation via RLS
-- - Row Level Security (RLS) enabled on all tenant-scoped tables
-- - Social media integration with Facebook caching
-- - Content pipeline automation system
-- - Channel grouping and management
-- - Analytics and usage tracking
-- - Subscription and billing management
-- - Workflow and approval systems
-- - Background task tracking and scraper jobs

-- Post-deployment checklist:
-- 1. Configure environment variables for database connection
-- 2. Set up authentication and tenant context middleware with set_config('app.current_tenant_id')
-- 3. Configure media storage and processing services (S3 integration)
-- 4. Update application code to use set_config for RLS tenant context
-- 5. Set up monitoring and alerting
-- 6. Run performance testing with expected data volumes
-- 7. Configure backup and disaster recovery procedures
-- 8. Test RLS policies with multiple tenant contexts

-- IMPORTANT: RLS Implementation Notes
-- - All queries must set the tenant context using: set_config('app.current_tenant_id', tenant_id, true)
-- - Service role client bypasses RLS - use regular client for tenant-scoped operations
-- - Newscard templates are globally accessible (not tenant-scoped)
-- - Cron jobs support both tenant-scoped and system-wide (NULL tenant_id) jobs