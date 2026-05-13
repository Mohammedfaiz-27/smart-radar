-- =====================================================
-- Add External News Integration to Posts Table
-- =====================================================
-- Links posts created from external news items back to the source
-- Enables bidirectional navigation: Post ↔ External News ↔ Publication
-- Created: 2025-01-16

-- Add external_news_id column to posts table
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS external_news_id UUID REFERENCES external_news_items(id) ON DELETE SET NULL;

-- Add index for efficient querying of external news posts
CREATE INDEX IF NOT EXISTS idx_posts_external_news_id ON posts(external_news_id);

-- Add comment to document the field
COMMENT ON COLUMN posts.external_news_id IS 'Reference to external news item if this post was created from external news publishing';

-- =====================================================
-- Update consolidated schema documentation
-- =====================================================
-- This migration adds support for tracking posts that were created
-- from external news items (NewsIt, RSS, etc.)
--
-- Usage:
-- - When publishing external news to channel groups, a post record is created
-- - The post.external_news_id links back to the source news item
-- - The external_news_publications.post_id links forward to the post
-- - This creates full bidirectional tracking
--
-- Example query to find all posts from external news:
-- SELECT p.*, e.title as news_title, e.external_source
-- FROM posts p
-- JOIN external_news_items e ON p.external_news_id = e.id
-- WHERE p.tenant_id = 'your-tenant-id'
-- ORDER BY p.created_at DESC;
-- =====================================================
