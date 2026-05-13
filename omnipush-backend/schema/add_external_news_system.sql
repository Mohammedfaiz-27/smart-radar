-- =====================================================
-- External News System
-- =====================================================
-- Generic system for ingesting, approving, and publishing external news
-- Supports NewsIt and other future external sources
-- Includes approval workflow and multi-channel-group publishing
-- Created: 2025-01-15

-- =====================================================
-- TABLE: external_news_items
-- =====================================================
-- Generic storage for news from external sources (NewsIt, RSS feeds, etc.)

CREATE TABLE IF NOT EXISTS external_news_items (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- External source tracking
    external_source VARCHAR(50) NOT NULL,  -- 'newsit', 'rss', 'custom', etc.
    external_id VARCHAR(255) NOT NULL,     -- Source's unique ID (e.g., NewsIt news_id)
    sqs_message_id VARCHAR(255),           -- For deduplication from SQS

    -- Core content (supports multilingual via JSONB)
    title VARCHAR(500) NOT NULL,           -- Default/primary language title
    content TEXT NOT NULL,                 -- Default/primary content
    multilingual_data JSONB,               -- Full multilingual structure: { "en": {...}, "ta": {...} }

    -- Metadata
    category VARCHAR(100),
    category_data JSONB,                   -- Multilingual category info
    topics JSONB,                          -- Array of topics with multilingual data
    tags TEXT[],

    -- Media
    images JSONB,                          -- All image variants: { "original_url": "...", "thumbnail_url": "...", "low_res_url": "..." }
    media_urls TEXT[],                     -- Additional media if any

    -- Source information
    source_url TEXT,
    source_name VARCHAR(255),

    -- Flags
    is_breaking BOOLEAN DEFAULT FALSE,

    -- Approval workflow
    approval_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Timestamps
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

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

-- =====================================================
-- TABLE: external_news_publications
-- =====================================================
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

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS
ALTER TABLE external_news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_news_publications ENABLE ROW LEVEL SECURITY;

-- RLS Policies for external_news_items
CREATE POLICY external_news_items_tenant_isolation ON external_news_items
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- RLS Policies for external_news_publications
CREATE POLICY external_news_pub_tenant_isolation ON external_news_publications
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- =====================================================
-- TABLE COMMENTS
-- =====================================================

COMMENT ON TABLE external_news_items IS 'Generic storage for news from external sources (NewsIt, RSS, etc.) with approval workflow and multilingual support';
COMMENT ON TABLE external_news_publications IS 'Tracks publishing history of external news to channel groups with status and results';

COMMENT ON COLUMN external_news_items.external_source IS 'Source system identifier: newsit, rss, custom, etc.';
COMMENT ON COLUMN external_news_items.external_id IS 'Unique ID from the external source system';
COMMENT ON COLUMN external_news_items.sqs_message_id IS 'SQS message ID for deduplication';
COMMENT ON COLUMN external_news_items.multilingual_data IS 'Full multilingual content structure as JSONB';
COMMENT ON COLUMN external_news_items.images IS 'Image URLs: original_url, thumbnail_url, low_res_url';
COMMENT ON COLUMN external_news_items.approval_status IS 'Approval workflow status: pending, approved, rejected';

COMMENT ON COLUMN external_news_publications.status IS 'Publishing status: pending, publishing, published, failed';
COMMENT ON COLUMN external_news_publications.publish_results IS 'Per-channel publishing results as JSONB';
COMMENT ON COLUMN external_news_publications.selected_language IS 'Language variant used for publishing';

-- =====================================================
-- END OF MIGRATION
-- =====================================================
