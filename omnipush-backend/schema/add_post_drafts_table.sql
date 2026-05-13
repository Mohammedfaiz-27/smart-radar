-- =====================================================
-- Post Drafts Table for Human-in-the-Loop Review
-- =====================================================
-- Migration to add post_drafts table for LLM-generated content review
-- Created: 2026-01-05
--
-- Purpose: Store LLM-generated content adaptations for human review before publishing
-- Workflow: Generate → Review → Approve/Reject → Publish
--
-- This table supports both:
-- 1. News Items module (external_news_items)
-- 2. Post Creator module (posts)

-- Create status enum for drafts
CREATE TYPE draft_status AS ENUM ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'PUBLISHED', 'FAILED');

-- Create post_drafts table
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

-- Indexes for performance
CREATE INDEX idx_post_drafts_tenant_id ON post_drafts(tenant_id);
CREATE INDEX idx_post_drafts_user_id ON post_drafts(user_id);
CREATE INDEX idx_post_drafts_status ON post_drafts(status);
CREATE INDEX idx_post_drafts_external_news_id ON post_drafts(external_news_id);
CREATE INDEX idx_post_drafts_post_id ON post_drafts(post_id);
CREATE INDEX idx_post_drafts_social_account_id ON post_drafts(social_account_id);
CREATE INDEX idx_post_drafts_created_at ON post_drafts(created_at DESC);
CREATE INDEX idx_post_drafts_status_created ON post_drafts(status, created_at DESC);

-- Row Level Security (RLS)
ALTER TABLE post_drafts ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see drafts from their tenant
CREATE POLICY post_drafts_tenant_isolation ON post_drafts
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Comments for documentation
COMMENT ON TABLE post_drafts IS 'Stores LLM-generated content adaptations for human review before publishing. Supports both external news and regular posts.';
COMMENT ON COLUMN post_drafts.external_news_id IS 'Link to external_news_items if this draft is from News Items module';
COMMENT ON COLUMN post_drafts.post_id IS 'Link to posts if this draft is from Post Creator module';
COMMENT ON COLUMN post_drafts.generated_content IS 'Original LLM-generated content (immutable)';
COMMENT ON COLUMN post_drafts.final_content IS 'User-edited content to be published (editable)';
COMMENT ON COLUMN post_drafts.status IS 'Workflow status: PENDING_REVIEW → APPROVED → PUBLISHED or REJECTED';
COMMENT ON COLUMN post_drafts.publish_result IS 'Result from social media API after publishing';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON post_drafts TO authenticated;
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO authenticated;
