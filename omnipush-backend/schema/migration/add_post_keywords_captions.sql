-- Add keywords and image_search_caption columns to posts table
-- These will store AI-generated metadata for posts

ALTER TABLE posts
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS image_search_caption VARCHAR(500);

-- Create index on keywords for faster searching
CREATE INDEX IF NOT EXISTS idx_posts_keywords ON posts USING GIN (keywords);

-- Add comment to document the columns
COMMENT ON COLUMN posts.keywords IS 'AI-generated keywords extracted from post content';
COMMENT ON COLUMN posts.image_search_caption IS 'AI-generated search term for finding relevant stock photos or AI-generated images';