-- =====================================================
-- Migration: Add S3 URL support to newscard_templates
-- =====================================================
-- This migration adds S3 URL field to store template files in S3
-- allowing templates to be pulled from cloud storage instead of local files

-- Add S3 URL column to newscard_templates table
ALTER TABLE newscard_templates
ADD COLUMN s3_url VARCHAR(1000),
ADD COLUMN s3_bucket VARCHAR(255),
ADD COLUMN s3_key VARCHAR(500);

-- Add index for S3 URL for faster lookups
CREATE INDEX idx_newscard_templates_s3_url ON newscard_templates(s3_url);

-- Comment on new columns
COMMENT ON COLUMN newscard_templates.s3_url IS 'Full S3 URL to the template file';
COMMENT ON COLUMN newscard_templates.s3_bucket IS 'S3 bucket name where template is stored';
COMMENT ON COLUMN newscard_templates.s3_key IS 'S3 key/path for the template file';