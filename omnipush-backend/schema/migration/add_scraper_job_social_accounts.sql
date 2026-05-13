-- Migration: Add support for account-based scraping to scraper jobs
-- Description: Creates table to store social account URLs and their resolved identifiers
-- for account-based scraping alongside keyword scraping
-- Date: 2026-01-14

-- Social Account Tracking Table for Scraper Jobs
CREATE TABLE IF NOT EXISTS scraper_job_social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_job_id UUID NOT NULL REFERENCES scraper_jobs(id) ON DELETE CASCADE,

    -- Account Information
    platform VARCHAR(50) NOT NULL,           -- 'facebook', 'twitter', etc.
    account_url TEXT NOT NULL,               -- Original URL provided by user
    account_identifier VARCHAR(255),         -- Resolved username/handle (e.g., '@username' or 'page-name')
    account_id VARCHAR(255),                 -- Platform-specific numeric/string account ID
    account_name VARCHAR(255),               -- Display name (if available from resolution)
    account_metadata JSONB DEFAULT '{}',     -- Additional platform-specific data

    -- Resolution Status
    resolution_status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'resolved', 'failed'
    resolution_error TEXT,                   -- Error message if resolution failed
    resolved_at TIMESTAMP WITH TIME ZONE,    -- When the account was successfully resolved
    last_validation_at TIMESTAMP WITH TIME ZONE,  -- Last time we verified account still exists

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_job_account UNIQUE(scraper_job_id, platform, account_url)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scraper_job_social_accounts_job_id
    ON scraper_job_social_accounts(scraper_job_id);

CREATE INDEX IF NOT EXISTS idx_scraper_job_social_accounts_status
    ON scraper_job_social_accounts(resolution_status);

CREATE INDEX IF NOT EXISTS idx_scraper_job_social_accounts_platform
    ON scraper_job_social_accounts(platform);

-- Row Level Security
ALTER TABLE scraper_job_social_accounts ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only access social accounts for jobs in their tenant
-- This policy joins to scraper_jobs table to check tenant_id
CREATE POLICY scraper_job_social_accounts_tenant_isolation ON scraper_job_social_accounts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM scraper_jobs
            WHERE scraper_jobs.id = scraper_job_social_accounts.scraper_job_id
            AND scraper_jobs.tenant_id = current_setting('app.current_tenant_id')::UUID
        )
    );

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_scraper_job_social_accounts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_scraper_job_social_accounts_updated_at
    BEFORE UPDATE ON scraper_job_social_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_scraper_job_social_accounts_updated_at();

-- Comments for documentation
COMMENT ON TABLE scraper_job_social_accounts IS 'Stores social media account URLs for account-based scraping in scraper jobs';
COMMENT ON COLUMN scraper_job_social_accounts.account_url IS 'Original URL provided by user (e.g., https://facebook.com/pagename)';
COMMENT ON COLUMN scraper_job_social_accounts.account_identifier IS 'Resolved username/handle extracted from URL';
COMMENT ON COLUMN scraper_job_social_accounts.account_id IS 'Platform-specific account ID (numeric for Facebook, handle for Twitter)';
COMMENT ON COLUMN scraper_job_social_accounts.resolution_status IS 'Status of account URL resolution: pending, resolved, or failed';
COMMENT ON COLUMN scraper_job_social_accounts.resolution_error IS 'Error message if account resolution failed (invalid URL, private account, etc.)';
