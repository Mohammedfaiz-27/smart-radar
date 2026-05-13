-- =====================================================
-- S3 Integration Schema Migration
-- Add S3 key tracking and update file path handling
-- =====================================================

-- Add S3 key columns to media table
ALTER TABLE media 
ADD COLUMN s3_key VARCHAR(500),
ADD COLUMN s3_bucket VARCHAR(100),
ADD COLUMN thumbnail_s3_key VARCHAR(500);

-- Add indexes for better performance on S3 key lookups
CREATE INDEX IF NOT EXISTS idx_media_s3_key ON media(s3_key);
CREATE INDEX IF NOT EXISTS idx_media_thumbnail_s3_key ON media(thumbnail_s3_key);

-- Update file_path column to be nullable (since we'll use S3 URLs)
ALTER TABLE media ALTER COLUMN file_path DROP NOT NULL;

-- Add comment to clarify the new structure
COMMENT ON COLUMN media.file_path IS 'Local file path or full S3 URL';
COMMENT ON COLUMN media.s3_key IS 'S3 object key for the main file';
COMMENT ON COLUMN media.s3_bucket IS 'S3 bucket name (optional, can use default)';
COMMENT ON COLUMN media.thumbnail_s3_key IS 'S3 object key for thumbnail file';

-- Add constraints to ensure either local path or S3 key is present
ALTER TABLE media ADD CONSTRAINT check_file_location 
CHECK (file_path IS NOT NULL OR s3_key IS NOT NULL);

-- Update any existing data (if needed)
-- This would typically be done with a data migration script
-- For now, just ensure the constraint allows existing data

-- Add S3 configuration to tenant_settings if not exists
-- INSERT INTO tenant_settings (tenant_id, setting_key, setting_value, created_at)
-- SELECT 
--     t.id as tenant_id,
--     'storage_backend' as setting_key,
--     '"s3"'::jsonb as setting_value,
--     NOW() as created_at
-- FROM tenants t
-- ON CONFLICT (tenant_id, setting_key) DO NOTHING;

-- -- Add default S3 bucket setting
-- INSERT INTO tenant_settings (tenant_id, setting_key, setting_value, created_at)
-- SELECT 
--     t.id as tenant_id,
--     's3_bucket' as setting_key,
--     '"omnipush-media"'::jsonb as setting_value,
--     NOW() as created_at
-- FROM tenants t
-- ON CONFLICT (tenant_id, setting_key) DO NOTHING;