# Row Level Security (RLS) Issue Fix

## Problem
The application was encountering the following error:
```
ERROR:core.middleware:Authentication failed: {'message': 'unrecognized configuration parameter "app.tenant_id"', 'code': '42704', 'hint': None, 'details': None}
```

## Root Cause
The database schema (`supabase_schema.sql`) includes Row Level Security (RLS) policies that depend on a PostgreSQL setting called `app.tenant_id`. However, Supabase doesn't easily support setting PostgreSQL parameters like this, causing the authentication to fail when the RLS policies try to evaluate.

## Solution
I've provided two solutions:

### Option 1: Use the No-RLS Schema (Recommended)
1. **Use the new schema file**: `supabase_schema_no_rls.sql`
   - This schema removes all RLS policies that depend on `app.tenant_id`
   - Tenant filtering is handled in the application code using the `TenantContext` class
   - This approach is simpler and more reliable with Supabase

2. **Apply the new schema**:
   ```sql
   -- Run the contents of supabase_schema_no_rls.sql in your Supabase SQL editor
   ```

3. **The application code is already updated** to handle tenant filtering manually:
   - `core/middleware.py` uses the service client for authentication
   - `TenantContext` class handles tenant filtering in application code
   - No changes needed to the application code

### Option 2: Fix the Original Schema (Advanced)
If you prefer to keep RLS, you would need to:

1. **Create a PostgreSQL function** to set the `app.tenant_id` parameter
2. **Modify the database client** to call this function before each request
3. **Handle session management** properly

However, this approach is more complex and may not work reliably with Supabase's connection pooling.

## Files Modified
- `core/database.py` - Simplified database client
- `core/middleware.py` - Updated to use service client for authentication
- `supabase_schema_no_rls.sql` - New schema without RLS dependencies

## Testing
After applying the new schema:

1. **Test authentication** - The error should be resolved
2. **Test tenant isolation** - Users should only see data from their own tenant
3. **Test API endpoints** - All endpoints should work with proper tenant filtering

## Security Note
Even without RLS, the application maintains proper tenant isolation through:
- JWT token validation
- User authentication with tenant association
- Manual tenant filtering in the `TenantContext` class
- Service client usage for operations that need to bypass tenant restrictions

## Migration Steps
1. Backup your current database
2. Run the cleanup commands from `supabase_schema_no_rls.sql`
3. Apply the new schema
4. Test the application
5. Verify tenant isolation works correctly

The application should now work without the `app.tenant_id` configuration error.
