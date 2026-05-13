-- Add news_item_id column to posts table for linking posts to news items
-- This enables posts to reference the original news article they were created from

-- Add the news_item_id column to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS news_item_id UUID REFERENCES news_items(id) ON DELETE SET NULL;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_news_item_id ON posts(news_item_id);

-- Add a comment to document the relationship
COMMENT ON COLUMN posts.news_item_id IS 'References the news_items.id for posts created from news articles';