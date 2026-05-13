# SQS Debug Mode Testing Guide

## Overview

The `test_sqs_mock_trigger.py` file now supports **DEBUG MODE** which invokes the actual `process_newsit_message` function to test the complete end-to-end flow.

## What is Debug Mode?

**Mock Mode (Default)**:
- Simulates message processing
- No external API calls
- No database writes
- Fast, lightweight testing

**Debug Mode**:
- ✅ Calls actual `process_newsit_message()` function
- ✅ Fetches real data from NewsIt API
- ✅ Stores in `external_news_items` table
- ✅ Checks for duplicates
- ✅ Full integration testing with real services

## Prerequisites

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment
Ensure `.env` file has:
```bash
# NewsIt API
NEWSIT_API_KEY=your-newsit-api-key
NEWSIT_API_URL=https://api.newsit.com

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

### 3. Database Setup
Ensure tables exist:
- `tenants` - Must have at least one tenant
- `external_news_items` - For storing news items

## Usage

### Method 1: Using `single-debug` Command

```bash
# Auto-detect tenant from database
uv run python test_sqs_mock_trigger.py single-debug

# With specific news ID
uv run python test_sqs_mock_trigger.py single-debug --news-id 691896c41a6aabeae05d0a66

# With specific tenant ID
uv run python test_sqs_mock_trigger.py single-debug --tenant-id 550e8400-e29b-41d4-a716-446655440000

# With both
uv run python test_sqs_mock_trigger.py single-debug \
  --news-id 691896c41a6aabeae05d0a66 \
  --tenant-id 550e8400-e29b-41d4-a716-446655440000
```

### Method 2: Using `--debug` Flag

```bash
# Enable debug mode on single scenario
uv run python test_sqs_mock_trigger.py single --debug

# With custom IDs
uv run python test_sqs_mock_trigger.py single --debug \
  --news-id 691896c41a6aabeae05d0a66 \
  --tenant-id 550e8400-e29b-41d4-a716-446655440000
```

## Complete Flow in Debug Mode

When you run debug mode, here's what happens:

```
1. SQS Message Created
   ↓
2. Message Added to Mock Queue
   ↓
3. Consumer Receives Message
   ↓
4. Parse Message Body
   ↓
5. Validate Structure (NewsItSQSMessage)
   ↓
6. 🐛 DEBUG MODE: Call process_newsit_message()
   ├─→ Fetch from NewsIt API
   ├─→ Transform to generic format
   ├─→ Check for duplicates in DB
   ├─→ Insert into external_news_items table
   └─→ Return result
   ↓
7. Display Result
   ├─→ Success/Failure
   ├─→ External News Item ID
   ├─→ Is Duplicate
   └─→ Error message (if any)
   ↓
8. Acknowledge or Retry
   └─→ Delete message (success) or Change visibility (retry)
```

## Example Output

### Successful Processing

```bash
$ uv run python test_sqs_mock_trigger.py single-debug --news-id 691896c41a6aabeae05d0a66

============================================================
SCENARIO 1: Single Message Processing
🐛 DEBUG MODE ENABLED
============================================================

✓ Using tenant from database: 550e8400-e29b-41d4-a716-446655440000

📤 Sending test message to queue...
   News ID: 691896c41a6aabeae05d0a66
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000
📨 Message added to queue: 4d35f04f-6e5d-4742-8ec6-3b935b651c5b

🚀 Starting mock SQS polling loop...

📬 Received 1 message(s) (iteration 1)

🔄 Processing message: 4d35f04f...
   News ID: 691896c41a6aabeae05d0a66
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000
   Source: newsit

🐛 DEBUG MODE: Calling actual process_newsit_message...
   This will:
   1. Validate message structure
   2. Fetch news from NewsIt API
   3. Transform to generic format
   4. Store in external_news_items table
   5. Check for duplicates

📊 Processing Result:
   Success: True
   External ID: 691896c41a6aabeae05d0a66
   External News Item ID: 123e4567-e89b-12d3-a456-426614174000
   Is Duplicate: False

✅ Message processed successfully via actual service
   ℹ️  New external news item created: 123e4567-e89b-12d3-a456-426614174000

📊 Batch result: 1/1 successful
✓ Queue empty, stopping...

📈 Final Statistics:
   Processed: 1
   Failed: 0
   Remaining: 0
```

### Duplicate Detection

```bash
🔄 Processing message: 4d35f04f...
   News ID: 691896c41a6aabeae05d0a66
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000
   Source: newsit

🐛 DEBUG MODE: Calling actual process_newsit_message...

📊 Processing Result:
   Success: True
   External ID: 691896c41a6aabeae05d0a66
   External News Item ID: 123e4567-e89b-12d3-a456-426614174000
   Is Duplicate: True

✅ Message processed successfully via actual service
   ℹ️  Item was a duplicate - no new record created
```

### Error Handling

```bash
🔄 Processing message: 4d35f04f...
   News ID: invalid-news-id
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000
   Source: newsit

🐛 DEBUG MODE: Calling actual process_newsit_message...

📊 Processing Result:
   Success: False
   External ID: invalid-news-id
   External News Item ID: None
   Is Duplicate: False
   ❌ Error: NewsIt API returned 404: News item not found

🕐 Message visibility changed: 300s delay
❌ Processing failed - message will retry
```

## Debugging Tips

### Enable Detailed Logging

Set logging level in the test file or via environment:

```bash
export LOG_LEVEL=DEBUG
uv run python test_sqs_mock_trigger.py single-debug
```

### Check Database

After running debug mode, verify data was stored:

```sql
-- Check external news items
SELECT id, external_id, title, approval_status, created_at
FROM external_news_items
WHERE external_source = 'newsit'
ORDER BY created_at DESC
LIMIT 10;

-- Check for specific news item
SELECT *
FROM external_news_items
WHERE external_id = '691896c41a6aabeae05d0a66';
```

### Common Issues

#### 1. "Debug mode not available"

**Error**:
```
❌ Debug mode not available!
   Please run: uv sync
```

**Solution**:
```bash
uv sync
```

#### 2. "No tenants found in database"

**Error**:
```
❌ No tenants found in database
   Please create a tenant first or provide tenant_id as argument
```

**Solution**:
```bash
# Option 1: Create a tenant in database
INSERT INTO tenants (id, name) VALUES (gen_random_uuid(), 'Test Tenant');

# Option 2: Provide tenant_id via command line
uv run python test_sqs_mock_trigger.py single-debug --tenant-id <your-tenant-id>
```

#### 3. NewsIt API Error

**Error**:
```
❌ Error: NewsIt API returned 404: News item not found
```

**Solution**:
- Verify news_id exists in NewsIt
- Check NEWSIT_API_KEY is valid
- Check NEWSIT_API_URL is correct
- Test API directly:
```bash
curl -H "Authorization: Bearer $NEWSIT_API_KEY" \
  https://api.newsit.com/news/691896c41a6aabeae05d0a66
```

#### 4. Database Connection Error

**Error**:
```
❌ Error accessing database: <connection error>
```

**Solution**:
- Verify SUPABASE_URL and SUPABASE_SERVICE_KEY in `.env`
- Check database connectivity
- Ensure tables exist

## Comparison: Mock vs Debug Mode

| Feature | Mock Mode | Debug Mode |
|---------|-----------|------------|
| **Speed** | Fast | Slower |
| **Dependencies** | None | uv sync required |
| **NewsIt API** | ❌ Simulated | ✅ Real API call |
| **Database** | ❌ No writes | ✅ Real writes |
| **Duplicate Check** | ❌ Simulated | ✅ Real check |
| **Data Created** | ❌ None | ✅ external_news_items |
| **Use Case** | Structure validation | Full integration test |
| **Setup Required** | None | .env, database |

## When to Use Each Mode

### Use Mock Mode When:
- ✓ Testing message structure
- ✓ Testing consumer flow
- ✓ Testing error handling
- ✓ Quick validation
- ✓ CI/CD pipelines
- ✓ No external dependencies available

### Use Debug Mode When:
- ✓ Testing actual NewsIt integration
- ✓ Validating data transformation
- ✓ Testing duplicate detection
- ✓ End-to-end integration testing
- ✓ Debugging production issues
- ✓ Verifying database schema

## Advanced Usage

### Test Multiple News Items

```bash
# Create a script to test multiple items
for news_id in 691896c41a6aabeae05d0a66 691896c41a6aabeae05d0a67 691896c41a6aabeae05d0a68; do
  echo "Testing news_id: $news_id"
  uv run python test_sqs_mock_trigger.py single-debug --news-id $news_id
  echo "---"
done
```

### Test with Breakpoints

Add breakpoints in the code for step-by-step debugging:

```python
# In test_sqs_mock_trigger.py, add before calling service:
import pdb; pdb.set_trace()

result = await self.news_service.process_newsit_message(...)
```

Then run:
```bash
uv run python test_sqs_mock_trigger.py single-debug
```

### Profile Performance

```bash
# Time the execution
time uv run python test_sqs_mock_trigger.py single-debug

# Or use Python profiler
uv run python -m cProfile -s cumtime test_sqs_mock_trigger.py single-debug
```

## Next Steps

After successful debug mode testing:

1. ✅ Verify data in database
2. ✅ Test with different news items
3. ✅ Test duplicate detection
4. ✅ Test error scenarios (invalid IDs, API errors)
5. 🚀 Deploy actual SQS consumer
6. 📊 Monitor production messages

## Related Documentation

- `TEST_SQS_README.md` - Quick start guide
- `docs/sqs_testing_guide.md` - Complete testing guide
- `docs/external_news_post_integration.md` - Integration architecture

## Troubleshooting

For issues, check:
1. Logs: Look for detailed error messages
2. Database: Verify data was created/updated
3. API: Test NewsIt API directly
4. Environment: Verify all .env variables are set

For questions or support, refer to the main documentation or check the codebase.
