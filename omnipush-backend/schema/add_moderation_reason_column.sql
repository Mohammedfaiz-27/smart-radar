-- Migration: Add moderation_reason column to news_items table
-- Date: 2025-10-01
-- Description: Adds moderation_reason column to store detailed feedback from content moderation

-- Add moderation_reason column to news_items
ALTER TABLE news_items
ADD COLUMN IF NOT EXISTS moderation_reason TEXT;

-- Add comment
COMMENT ON COLUMN news_items.moderation_reason IS 'Detailed reason for moderation decision (approval/rejection)';


-- Add moderation_reason column to news_items
ALTER TABLE external_news_items
ADD COLUMN IF NOT EXISTS moderation_reason TEXT,
ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP WITH TIME ZONE;

-- Add comment
COMMENT ON COLUMN external_news_items.moderation_reason IS 'Detailed reason for moderation decision (approval/rejection)';
