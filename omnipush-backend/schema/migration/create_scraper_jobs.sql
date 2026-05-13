-- Social Media Scraper Jobs Configuration Table
CREATE TABLE IF NOT EXISTS scraper_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT[] NOT NULL DEFAULT '{}',
    platforms TEXT[] NOT NULL DEFAULT '{}', -- facebook, twitter, instagram, etc.
    schedule_cron VARCHAR(100) NOT NULL DEFAULT '*/5 * * * *', -- Every 5 minutes by default
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    settings JSONB DEFAULT '{}', -- Additional configuration like max_posts, filters, etc.
    post_approval_logic TEXT, -- Natural language approval/rejection logic
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
CREATE TABLE IF NOT EXISTS scraper_job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_job_id UUID NOT NULL REFERENCES scraper_jobs(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'running', -- running, completed, failed
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_tenant_id ON scraper_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_enabled ON scraper_jobs(is_enabled) WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_next_run ON scraper_jobs(next_run_at) WHERE is_enabled = true;
CREATE INDEX IF NOT EXISTS idx_scraper_job_runs_job_id ON scraper_job_runs(scraper_job_id);
CREATE INDEX IF NOT EXISTS idx_scraper_job_runs_tenant_id ON scraper_job_runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scraper_job_runs_status ON scraper_job_runs(status);

-- Row Level Security Policies
ALTER TABLE scraper_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_job_runs ENABLE ROW LEVEL SECURITY;

-- Policy for scraper_jobs
CREATE POLICY scraper_jobs_tenant_isolation ON scraper_jobs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Policy for scraper_job_runs
CREATE POLICY scraper_job_runs_tenant_isolation ON scraper_job_runs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

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