-- LLM Logs Table for tracking all LLM API calls and responses
-- This provides observability, debugging, and usage analytics

CREATE TABLE IF NOT EXISTS llm_logs (
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

-- Indexes for performance
CREATE INDEX idx_llm_logs_tenant_id ON llm_logs(tenant_id);
CREATE INDEX idx_llm_logs_created_at ON llm_logs(created_at DESC);
CREATE INDEX idx_llm_logs_profile ON llm_logs(profile);
CREATE INDEX idx_llm_logs_model ON llm_logs(model);
CREATE INDEX idx_llm_logs_status ON llm_logs(status);
CREATE INDEX idx_llm_logs_service_name ON llm_logs(service_name);
CREATE INDEX idx_llm_logs_tenant_created ON llm_logs(tenant_id, created_at DESC);

-- RLS Policies
ALTER TABLE llm_logs ENABLE ROW LEVEL SECURITY;

-- Tenant isolation: Users can only see logs for their tenant
CREATE POLICY llm_logs_tenant_isolation ON llm_logs
    FOR SELECT
    USING (
        tenant_id IN (
            SELECT tenant_id FROM users WHERE id = auth.uid()
        )
    );

-- Allow service role full access (for backend logging)
CREATE POLICY llm_logs_service_role ON llm_logs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Comments for documentation
COMMENT ON TABLE llm_logs IS 'Logs all LLM API calls for observability, debugging, and analytics';
COMMENT ON COLUMN llm_logs.profile IS 'LLM profile used: DEFAULT, PRECISE, CREATIVE, or ANALYTICAL';
COMMENT ON COLUMN llm_logs.operation IS 'Type of operation: generate, stream, or batch_generate';
COMMENT ON COLUMN llm_logs.messages IS 'Full message history sent to LLM';
COMMENT ON COLUMN llm_logs.response_content IS 'Generated text response from LLM';
COMMENT ON COLUMN llm_logs.execution_time_ms IS 'Time taken to complete the LLM request in milliseconds';
COMMENT ON COLUMN llm_logs.service_name IS 'Service that initiated the LLM call (e.g., ai_content_service)';

-- View for analytics
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
