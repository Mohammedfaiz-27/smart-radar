# Tests Directory

## Overview

This directory contains test files for the External News SQS integration system.

## Test Files

### 1. `test_sqs_mock_trigger.py` - Main SQS Testing Tool ⭐

**Primary test file for SQS message processing**

- **Debug Mode by Default**: Running `single` scenario automatically invokes actual `process_newsit_message()` function
- **Full Integration**: Fetches from NewsIt API, stores in database, checks duplicates
- **Easy Debugging**: Set breakpoints and step through the complete flow

**Usage from project root**:

```bash
# Run with actual process_newsit_message (DEBUG MODE - DEFAULT for 'single')
uv run python tests/test_sqs_mock_trigger.py single

# With specific news ID
uv run python tests/test_sqs_mock_trigger.py single --news-id 691896c41a6aabeae05d0a66

# With specific tenant ID
uv run python tests/test_sqs_mock_trigger.py single --tenant-id <your-tenant-id>

# With both
uv run python tests/test_sqs_mock_trigger.py single \
  --news-id 691896c41a6aabeae05d0a66 \
  --tenant-id <your-tenant-id>

# Other scenarios (mock mode)
python3 tests/test_sqs_mock_trigger.py batch
python3 tests/test_sqs_mock_trigger.py error
```

**What 'single' scenario does**:
1. ✅ Creates mock SQS message
2. ✅ Calls actual `process_newsit_message()` function
3. ✅ Fetches news from NewsIt API
4. ✅ Transforms to generic format
5. ✅ Stores in `external_news_items` table
6. ✅ Checks for duplicates
7. ✅ Returns detailed result

**Prerequisites for 'single' scenario**:
```bash
# Install dependencies
uv sync

# Configure .env
NEWSIT_API_KEY=your-key
NEWSIT_API_URL=https://api.newsit.com
SUPABASE_URL=your-url
SUPABASE_SERVICE_KEY=your-key
```

---

### 2. `test_sqs_message.py` - Sample Payloads & Validation

**For viewing SQS message formats and structure validation**

```bash
# View sample payloads (no dependencies required)
python3 tests/test_sqs_message.py --samples-only

# Full integration test (requires setup)
uv run python tests/test_sqs_message.py <tenant_id> <news_id>
```

---

### 3. `test_external_news_integration.py` - Post Integration Test

**Tests the External News → Posts module integration**

```bash
uv run python tests/test_external_news_integration.py
```

Validates:
- Post record creation
- External news linking
- Publishing flow
- Channel group integration

---

## Quick Start

### For Debugging Complete Flow

```bash
# 1. Install dependencies
uv sync

# 2. Run debug mode (invokes actual process_newsit_message)
uv run python tests/test_sqs_mock_trigger.py single --news-id <newsit-id>

# 3. Set breakpoints in your IDE in:
#    - services/external_news_service.py (process_newsit_message)
#    - services/newsit_client.py (fetch_and_transform)
#    Then run in debug mode
```

### For Quick Structure Validation

```bash
# No setup required
python3 tests/test_sqs_mock_trigger.py batch
python3 tests/test_sqs_message.py --samples-only
```

---

## Running from Different Locations

All test files use relative paths and can be run from the project root:

```bash
# From omnipush-backend/ directory
python3 tests/test_sqs_mock_trigger.py single
uv run python tests/test_sqs_message.py --samples-only
```

---

## Test Scenarios

### test_sqs_mock_trigger.py Scenarios

| Scenario | Debug Mode | Description |
|----------|------------|-------------|
| `single` | ✅ Yes (Default) | Calls actual process_newsit_message - **USE THIS FOR DEBUGGING** |
| `single-debug` | ✅ Yes | Same as `single` (alias) |
| `batch` | ❌ Mock | Simulates 3 messages |
| `error` | ❌ Mock | Tests error handling |
| `continuous` | ❌ Mock | Tests polling loop |
| `custom` | ❌ Mock | Custom message IDs |

---

## Debugging Tips

### Using with IDE Debugger

1. **Set breakpoints in**:
   - `services/external_news_service.py` → `process_newsit_message()`
   - `services/newsit_client.py` → `fetch_and_transform()`
   - `tests/test_sqs_mock_trigger.py` → `process_message()`

2. **Run in debug mode**:
   ```bash
   # VS Code, PyCharm, etc.
   uv run python tests/test_sqs_mock_trigger.py single --news-id <id>
   ```

3. **Step through the flow**:
   - Message creation
   - SQS message parsing
   - process_newsit_message invocation
   - NewsIt API fetch
   - Data transformation
   - Database insertion
   - Duplicate check

### Check Results in Database

```sql
-- View latest external news items
SELECT id, external_id, title, approval_status, created_at
FROM external_news_items
ORDER BY created_at DESC
LIMIT 10;

-- Check specific item
SELECT *
FROM external_news_items
WHERE external_id = '691896c41a6aabeae05d0a66';
```

---

## Environment Setup

### Required for Debug Mode

```bash
# .env file
NEWSIT_API_KEY=your-newsit-api-key
NEWSIT_API_URL=https://api.newsit.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

### Database Tables Required

- `tenants` - For tenant lookup
- `external_news_items` - For storing news
- `external_news_publications` - For publishing tracking

---

## Sample Output

### Debug Mode (single scenario)

```bash
$ uv run python tests/test_sqs_mock_trigger.py single --news-id 691896c41a6aabeae05d0a66

============================================================
SCENARIO 1: Single Message Processing
🐛 DEBUG MODE ENABLED
============================================================

✓ Using tenant from database: 550e8400-e29b-41d4-a716-446655440000

📤 Sending test message to queue...
   News ID: 691896c41a6aabeae05d0a66
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000

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
```

---

## Documentation

For detailed guides, see:

- `TEST_SQS_README.md` - Quick start guide
- `DEBUG_MODE_GUIDE.md` - Complete debug mode documentation
- `../docs/sqs_testing_guide.md` - Full testing guide
- `../docs/external_news_post_integration.md` - Integration architecture

---

## Troubleshooting

### "Debug mode not available"

```bash
# Install dependencies
uv sync
```

### "No tenants found in database"

```bash
# Provide tenant ID explicitly
uv run python tests/test_sqs_mock_trigger.py single --tenant-id <your-tenant-id>
```

### NewsIt API Error

```bash
# Verify credentials in .env
echo $NEWSIT_API_KEY

# Test API directly
curl -H "Authorization: Bearer $NEWSIT_API_KEY" \
  https://api.newsit.com/news/691896c41a6aabeae05d0a66
```

---

## Best Practices

1. **Always test with actual NewsIt news IDs** - Don't use random IDs
2. **Check database after tests** - Verify data was created correctly
3. **Use debug mode for development** - Set breakpoints and step through
4. **Test duplicate detection** - Run same message twice
5. **Test error scenarios** - Invalid IDs, API errors, etc.

---

## Next Steps

After running tests successfully:

1. ✅ Deploy SQS consumer: `./start_newsit_consumer.sh start`
2. ✅ Monitor logs: `./start_newsit_consumer.sh logs -f`
3. ✅ Test with real SQS messages
4. ✅ Set up monitoring and alerts
