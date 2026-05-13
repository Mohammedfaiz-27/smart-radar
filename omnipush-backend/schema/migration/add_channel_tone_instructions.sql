-- Add content tone and custom instructions fields to social_accounts table
-- Migration script to add channel-specific content customization options

-- Add new columns to social_accounts table
ALTER TABLE social_accounts 
ADD COLUMN IF NOT EXISTS content_tone VARCHAR(50) DEFAULT 'professional',
ADD COLUMN IF NOT EXISTS custom_instructions TEXT;

-- Add index for content_tone for better query performance
CREATE INDEX IF NOT EXISTS idx_social_accounts_content_tone ON social_accounts(content_tone);

-- Add comments for documentation
COMMENT ON COLUMN social_accounts.content_tone IS 'Content tone/style for this social channel (e.g., professional, casual, friendly, formal)';
COMMENT ON COLUMN social_accounts.custom_instructions IS 'Custom AI prompt instructions specific to this social channel for content generation and customization';