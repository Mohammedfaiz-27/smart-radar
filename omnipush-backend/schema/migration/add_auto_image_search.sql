-- Add auto_image_search setting to social_accounts table
-- This enables automatic image search and attachment when publishing posts

ALTER TABLE social_accounts
ADD COLUMN IF NOT EXISTS auto_image_search BOOLEAN DEFAULT FALSE;

-- Add comment to document the column
COMMENT ON COLUMN social_accounts.auto_image_search IS 'Enable automatic image search and attachment when publishing posts based on image_search_caption';