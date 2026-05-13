-- =====================================================
-- Add city_data column to external_news_items
-- =====================================================
-- Adds support for storing city/district information with multilingual names
-- City data structure: { "name": "...", "multilingual_names": { "en": "...", "ta": "..." } }
-- Created: 2025-01-29

-- Add city_data column to external_news_items table
ALTER TABLE external_news_items
ADD COLUMN IF NOT EXISTS city_data JSONB;

-- Add comment for the new column
COMMENT ON COLUMN external_news_items.city_data IS 'City/district information with multilingual names';

-- Create index for city_data JSONB queries
CREATE INDEX IF NOT EXISTS idx_external_news_city_data
ON external_news_items USING GIN (city_data);

-- =====================================================
-- END OF MIGRATION
-- =====================================================
