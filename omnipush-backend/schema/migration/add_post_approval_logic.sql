-- Add post_approval_logic field to scraper_jobs table
-- This field allows users to define custom approval/rejection logic for posts in natural language
-- The logic will be interpreted by AI during the moderation process

ALTER TABLE scraper_jobs
ADD COLUMN IF NOT EXISTS post_approval_logic TEXT;

COMMENT ON COLUMN scraper_jobs.post_approval_logic IS 'Natural language description of approval/rejection logic for posts. If null, default moderation logic is used.';

-- Example values:
-- 'Only approve posts about technology and AI with positive sentiment'
-- 'Approve local Coimbatore news, reject political or promotional content'
-- 'Accept breaking news less than 2 hours old from verified sources'