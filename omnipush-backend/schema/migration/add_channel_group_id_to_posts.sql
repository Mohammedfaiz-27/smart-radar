-- Migration: Add channel_group_id to posts table
-- This allows posts to be associated with channel groups for easier publishing

-- Add channel_group_id column to posts table
ALTER TABLE posts 
ADD COLUMN channel_group_id UUID REFERENCES channel_groups(id) ON DELETE SET NULL;

-- Add index for performance
CREATE INDEX idx_posts_channel_group_id ON posts(channel_group_id);

-- Update RLS policy to include channel_group_id (optional, for future use)
-- Note: The existing RLS policies on posts should still work as they filter by tenant_id