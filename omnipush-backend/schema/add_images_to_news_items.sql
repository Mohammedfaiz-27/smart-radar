-- Migration: Add images field to news_items table
-- Purpose: Store scraped social media post images
-- Date: 2025-12-11

-- Add images JSONB column to store image URLs (original, thumbnail, low_res)
ALTER TABLE news_items
ADD COLUMN IF NOT EXISTS images JSONB;

-- Add comment for documentation
COMMENT ON COLUMN news_items.images IS 'Scraped post images in format: {original_url, thumbnail_url, low_res_url}';
