# SQS Message Testing - Quick Start

## Test Files Overview

This directory contains two test files for validating SQS message processing:

### 1. `test_sqs_mock_trigger.py` ⭐ **START HERE**

**Best for**: Quick testing without any setup (Mock Mode) OR Full integration testing (Debug Mode)

**Mock Mode** (Default):
- ✅ No dependencies required
- ✅ No AWS credentials needed
- ✅ No database needed
- ✅ Runs completely offline

**Debug Mode** 🐛 (New!):
- ✅ Calls actual `process_newsit_message()` function
- ✅ Fetches from NewsIt API
- ✅ Stores in database
- ✅ Full integration testing
- ⚙️ Requires: `uv sync`, `.env` config, database

**Quick Start**:

```bash
# Mock Mode (no setup)
python3 test_sqs_mock_trigger.py single

# Debug Mode (full integration)
uv run python test_sqs_mock_trigger.py single-debug

# Debug Mode with specific IDs
uv run python test_sqs_mock_trigger.py single-debug \
  --news-id 691896c41a6aabeae05d0a66 \
  --tenant-id <your-tenant-id>
```

**What it does**:
- **Mock Mode**: Simulates SQS message delivery, validates structure
- **Debug Mode**: Complete end-to-end flow with real API calls and database

---

### 2. `test_sqs_message.py`

**Best for**: Full integration testing with real services

- ⚙️ Requires: `uv sync` (dependencies)
- ⚙️ Requires: AWS credentials
- ⚙️ Requires: Database access
- ⚙️ Connects to actual NewsIt API

**Quick Start**:
```bash
# View sample payloads (no setup required)
python3 test_sqs_message.py --samples-only

# Full integration test (requires setup)
uv run python test_sqs_message.py <tenant_id> <news_id>
```

**What it does**:
- Displays sample SQS message payloads
- Tests actual message processing
- Fetches from NewsIt API
- Creates records in database

---

## Quick Test Commands

### 1. Test Mock SQS (No Setup)
```bash
python3 test_sqs_mock_trigger.py single
```

### 2. Test Debug Mode - Full Integration 🐛 (Requires Setup)
```bash
# Install dependencies
uv sync

# Run debug mode with actual service
uv run python test_sqs_mock_trigger.py single-debug

# Or with specific news ID
uv run python test_sqs_mock_trigger.py single-debug --news-id 691896c41a6aabeae05d0a66
```

### 3. View SQS Message Samples (No Setup)
```bash
python3 test_sqs_message.py --samples-only
```

### 4. Test with Custom Message (No Setup)
```bash
python3 test_sqs_mock_trigger.py custom newsit-123 550e8400-e29b-41d4-a716-446655440000
```

---

## Sample SQS Message

```json
{
  "MessageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
  "ReceiptHandle": "MessageReceiptHandle",
  "Body": "{\"news_id\":\"newsit-123456\",\"tenant_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"source\":\"newsit\",\"metadata\":{\"trigger_time\":\"2025-01-16T10:30:00Z\"}}",
  "Attributes": {
    "SentTimestamp": "1705405800000",
    "ApproximateReceiveCount": "1"
  }
}
```

**Message Body (Payload)**:
```json
{
  "news_id": "newsit-123456",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "newsit",
  "metadata": {
    "trigger_time": "2025-01-16T10:30:00Z",
    "trigger_source": "newsit_webhook"
  }
}
```

---

## Testing Flow

```
┌─────────────────────────────────────────────────────┐
│  1. Start with Mock Testing (No Setup)             │
│     python3 test_sqs_mock_trigger.py all           │
│                                                     │
│     Validates: Message structure, flow, errors     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  2. View Sample Payloads                           │
│     python3 test_sqs_message.py --samples-only     │
│                                                     │
│     Shows: Message formats, schemas, examples      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  3. Integration Testing (With Setup)               │
│     uv sync                                        │
│     uv run python test_sqs_message.py <tenant_id>  │
│                                                     │
│     Tests: API fetch, database, full flow          │
└─────────────────────────────────────────────────────┘
```

---

## Test Scenarios

### Mock Testing Scenarios

| Scenario | Command | What it tests |
|----------|---------|---------------|
| Single Message | `python3 test_sqs_mock_trigger.py single` | Basic message processing |
| Batch | `python3 test_sqs_mock_trigger.py batch` | Multiple messages at once |
| Error Handling | `python3 test_sqs_mock_trigger.py error` | Malformed messages, missing fields |
| Continuous | `python3 test_sqs_mock_trigger.py continuous` | Polling loop simulation |
| Custom | `python3 test_sqs_mock_trigger.py custom <news_id> <tenant_id>` | Your own message |

---

## Expected Output

### Mock Test Success ✅
```
============================================================
SCENARIO 1: Single Message Processing
============================================================

📤 Sending test message to queue...
📨 Message added to queue: 4d35f04f-6e5d-4742-8ec6-3b935b651c5b

🚀 Starting mock SQS polling loop...

📬 Received 1 message(s) (iteration 1)

🔄 Processing message: 4d35f04f...
   News ID: newsit-test-001
   Tenant ID: 550e8400-e29b-41d4-a716-446655440000
   Source: newsit
   ✓ Message validated
   ✓ Ready for NewsIt API fetch
   ✓ Ready to store in database
✅ Message processed successfully

📊 Batch result: 1/1 successful
✓ Queue empty, stopping...

📈 Final Statistics:
   Processed: 1
   Failed: 0
   Remaining: 0
```

---

## Troubleshooting

### Error: "No module named 'pydantic_settings'"

**Solution**: Use mock testing or install dependencies
```bash
# Option 1: Use mock testing (no dependencies)
python3 test_sqs_mock_trigger.py all

# Option 2: Install dependencies
uv sync
```

### Error: "AWS credentials not configured"

**Solution**: Mock testing doesn't need AWS credentials
```bash
python3 test_sqs_mock_trigger.py all
```

For integration testing, configure `.env`:
```bash
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_SQS_QUEUE_URL=your-queue-url
```

---

## Documentation

For detailed testing guide, see: `docs/sqs_testing_guide.md`

For external news integration, see: `docs/external_news_post_integration.md`

---

## Quick Reference

| Task | Command |
|------|---------|
| Mock test all scenarios | `python3 test_sqs_mock_trigger.py all` |
| Mock test single message | `python3 test_sqs_mock_trigger.py single` |
| View sample payloads | `python3 test_sqs_message.py --samples-only` |
| Help for mock testing | `python3 test_sqs_mock_trigger.py --help` |
| Help for integration test | `python3 test_sqs_message.py --help` |

---

## Next Steps

After testing:

1. ✅ Mock tests pass → Message structure is correct
2. ✅ Sample payloads reviewed → Understand message format
3. ✅ Integration tests pass → Full flow works
4. 🚀 Deploy consumer: `./start_newsit_consumer.sh start`
5. 📊 Monitor: `./start_newsit_consumer.sh logs -f`
