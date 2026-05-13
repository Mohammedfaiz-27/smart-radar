-- Migration: Add background task support to posts table
-- Description: Adds fields to track background processing status and task IDs

-- Add new columns to posts table for background task tracking
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS processing_task_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Create index on processing_task_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_posts_processing_task_id ON posts(processing_task_id);

-- Create index on status for faster status filtering
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);

-- Add comment for documentation
COMMENT ON COLUMN posts.processing_task_id IS 'ID of the background task currently processing this post';
COMMENT ON COLUMN posts.error_message IS 'Error message if post processing failed';
COMMENT ON COLUMN posts.metadata IS 'Additional metadata for post processing and results';

-- Create background_tasks table for task management (optional - tasks are currently stored in memory)
CREATE TABLE IF NOT EXISTS background_tasks (
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

-- Create indexes for background_tasks table
CREATE INDEX IF NOT EXISTS idx_background_tasks_task_id ON background_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_tenant_id ON background_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status);
CREATE INDEX IF NOT EXISTS idx_background_tasks_created_at ON background_tasks(created_at);

-- Enable RLS on background_tasks table
ALTER TABLE background_tasks ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for tenant isolation
CREATE POLICY background_tasks_tenant_isolation ON background_tasks
    FOR ALL
    USING (tenant_id = (current_setting('app.current_tenant_id')::UUID))
    WITH CHECK (tenant_id = (current_setting('app.current_tenant_id')::UUID));

-- Grant permissions
GRANT ALL ON background_tasks TO authenticated;
GRANT ALL ON background_tasks TO service_role;

-- Add comments for documentation
COMMENT ON TABLE background_tasks IS 'Background task tracking and management';
COMMENT ON COLUMN background_tasks.task_id IS 'Unique identifier for the background task';
COMMENT ON COLUMN background_tasks.task_type IS 'Type of background task (e.g., publish_post, generate_newscard)';
COMMENT ON COLUMN background_tasks.status IS 'Current status of the task (pending, processing, completed, failed)';
COMMENT ON COLUMN background_tasks.data IS 'Input data for the task';
COMMENT ON COLUMN background_tasks.result IS 'Result data from the completed task';
COMMENT ON COLUMN background_tasks.progress IS 'Progress tracking information';