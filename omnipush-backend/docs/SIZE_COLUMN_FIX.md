# Media Size Column Fix

## Problem
The application was throwing an error: `column media.size does not exist` when trying to calculate storage usage for tenants.

## Root Cause
The database schema defined a `size` column in the `media` table, but this column was not actually created in the Supabase database.

## Solution Applied

### 1. Code Changes (Immediate Fix)
- Modified `api/v1/tenants.py` to handle missing `size` column gracefully with fallback calculation
- Updated `api/v1/media.py` to conditionally include `size` field when inserting media records
- Made `size` field optional in `models/media.py` response models

### 2. Database Fix (Long-term Solution)
Run the SQL script `add_size_column.sql` in your Supabase SQL editor:

```sql
-- Add size column to media table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'media' 
        AND column_name = 'size'
    ) THEN
        ALTER TABLE media ADD COLUMN size INTEGER;
        COMMENT ON COLUMN media.size IS 'File size in bytes';
    END IF;
END $$;

-- Update existing records with estimated sizes
UPDATE media 
SET size = 1024000  -- Default to 1MB for existing records
WHERE size IS NULL;
```

## How to Apply the Fix

1. **Immediate Fix (Already Applied)**: The code changes have been made to handle the missing column gracefully.

2. **Database Fix**: 
   - Go to your Supabase project dashboard
   - Navigate to the SQL Editor
   - Run the contents of `add_size_column.sql`
   - This will add the missing column and set default values for existing records

## Verification
After applying the database fix, the storage usage calculation should work correctly. You can verify by:
1. Checking the tenant details endpoint: `GET /v1/tenants/me`
2. Looking for the `current_usage.storage_used_gb` field in the response

## Notes
- The fallback calculation estimates 1MB per media file when the exact size is not available
- New media uploads will include the actual file size
- Existing media records will be updated with an estimated size of 1MB
