-- Verification script for LLM logging schema
-- Run this after applying add_llm_logs_table.sql to verify everything is set up correctly

-- 1. Check if llm_logs table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'llm_logs'
) as llm_logs_exists;

-- 2. Check table structure
\d llm_logs

-- 3. Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'llm_logs'
ORDER BY indexname;

-- 4. Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'llm_logs';

-- 5. Verify RLS is enabled
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename = 'llm_logs';

-- 6. Check if llm_usage_stats view exists
SELECT EXISTS (
    SELECT FROM information_schema.views
    WHERE table_schema = 'public'
    AND table_name = 'llm_usage_stats'
) as llm_usage_stats_exists;

-- 7. Test inserting a sample log entry (as service role)
-- This should succeed
INSERT INTO llm_logs (
    tenant_id,
    profile,
    model,
    operation,
    messages,
    response_content,
    status,
    execution_time_ms,
    temperature,
    max_tokens,
    prompt_tokens,
    completion_tokens,
    total_tokens,
    service_name
) VALUES (
    gen_random_uuid(),
    'DEFAULT',
    'gpt-4o-mini',
    'generate',
    '[{"role": "user", "content": "test"}]'::jsonb,
    'This is a test response',
    'success',
    1500,
    0.7,
    100,
    10,
    15,
    25,
    'test_script'
) RETURNING id, created_at;

-- 8. Verify the insert worked
SELECT COUNT(*) as total_logs FROM llm_logs;

-- 9. Test the usage stats view
SELECT * FROM llm_usage_stats LIMIT 1;

-- 10. Clean up test data
DELETE FROM llm_logs WHERE service_name = 'test_script';

-- All checks passed!
SELECT '✅ LLM logging schema verified successfully!' as status;
