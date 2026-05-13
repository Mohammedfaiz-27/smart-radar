-- Add publish_results column to posts table
-- This column stores the results of background publishing operations

ALTER TABLE posts ADD COLUMN IF NOT EXISTS publish_results JSONB DEFAULT '{}';

-- Add comment for documentation
COMMENT ON COLUMN posts.publish_results IS 'JSON structure storing publishing results from background tasks, including platform-specific responses and errors';

-- Create index for querying publish results
CREATE INDEX IF NOT EXISTS idx_posts_publish_results ON posts USING GIN (publish_results);