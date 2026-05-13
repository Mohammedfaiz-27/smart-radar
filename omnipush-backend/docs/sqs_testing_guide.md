# SQS Message Testing Guide

## Overview

This guide explains how to test the NewsIt SQS integration using the provided test tools.

## Test Files

### 1. `test_sqs_message.py` - Full Integration Testing

**Purpose**: Validates actual SQS message processing with real AWS SQS and NewsIt API.

**Features**:
- ✓ Sample SQS message payload generation
- ✓ Message structure validation
- ✓ Actual message processing with NewsIt API
- ✓ Database integration testing
- ✓ Error handling validation
- ✓ Batch processing tests

**Requirements**:
- AWS credentials configured in `.env`
- Valid SQS queue URL
- NewsIt API credentials
- Database access
- Valid tenant UUID
- Valid NewsIt news item ID (optional)

**Usage**:

```bash
# View sample payloads only
python test_sqs_message.py --samples-only

# Test with actual processing
python test_sqs_message.py <tenant_id> [news_id]

# Example
python test_sqs_message.py 550e8400-e29b-41d4-a716-446655440000 newsit-12345
```

**What It Tests**:
1. Message structure validation
2. Payload validation (NewsItSQSMessage schema)
3. NewsIt API fetching
4. External news item creation in database
5. Duplicate detection
6. Error handling

---

### 2. `test_sqs_mock_trigger.py` - Mock Testing

**Purpose**: Simulates SQS message delivery without requiring AWS or external APIs.

**Features**:
- ✓ Mock SQS service (no AWS credentials needed)
- ✓ Multiple test scenarios
- ✓ Message flow validation
- ✓ Error handling simulation
- ✓ Batch processing simulation
- ✓ Continuous polling simulation

**Requirements**:
- No external dependencies
- No AWS credentials
- No database (validates structure only)

**Usage**:

```bash
# Run all scenarios
python test_sqs_mock_trigger.py all

# Run specific scenarios
python test_sqs_mock_trigger.py single     # Single message
python test_sqs_mock_trigger.py batch      # Batch processing
python test_sqs_mock_trigger.py error      # Error handling
python test_sqs_mock_trigger.py continuous # Continuous polling

# Custom message test
python test_sqs_mock_trigger.py custom newsit-123 550e8400-e29b-41d4-a716-446655440000
```

**Test Scenarios**:

1. **Single Message**: Tests processing one message
2. **Batch Processing**: Tests processing 3 messages at once
3. **Error Handling**: Tests malformed messages and missing fields
4. **Continuous Polling**: Tests polling loop with multiple iterations
5. **Custom Messages**: Tests with your own news_id and tenant_id

---

## SQS Message Structure

### Complete SQS Message Format

```json
{
  "MessageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
  "ReceiptHandle": "MessageReceiptHandle",
  "Body": "{\"news_id\":\"newsit-123456\",\"tenant_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"source\":\"newsit\",\"metadata\":{\"trigger_time\":\"2025-01-16T10:30:00Z\",\"trigger_source\":\"newsit_webhook\"}}",
  "Attributes": {
    "SentTimestamp": "1705405800000",
    "ApproximateReceiveCount": "1",
    "ApproximateFirstReceiveTimestamp": "1705405800000",
    "SenderId": "AIDAIT2UOQQY3AUEKVGXU"
  },
  "MessageAttributes": {
    "Priority": {
      "StringValue": "high",
      "DataType": "String"
    },
    "Source": {
      "StringValue": "newsit",
      "DataType": "String"
    }
  },
  "MD5OfBody": "7b270e59b47ff90a553787216d55d91d",
  "MD5OfMessageAttributes": "00484c68-...",
  "EventSource": "aws:sqs",
  "EventSourceARN": "arn:aws:sqs:us-east-1:123456789012:newsit-queue",
  "AwsRegion": "us-east-1"
}
```

### Message Body (Payload) Format

```json
{
  "news_id": "newsit-123456",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "newsit",
  "metadata": {
    "trigger_time": "2025-01-16T10:30:00Z",
    "trigger_source": "newsit_webhook",
    "priority": "high",
    "is_breaking": true,
    "category": "politics",
    "language": "en"
  }
}
```

### Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `news_id` | string | Yes | NewsIt news item ID |
| `tenant_id` | UUID | Yes | Tenant UUID for routing |
| `source` | string | No | Source identifier (default: "newsit") |
| `metadata` | object | No | Additional metadata |

### Optional Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `trigger_time` | ISO datetime | When message was triggered |
| `trigger_source` | string | Source that triggered message |
| `priority` | string | Message priority (high/normal/low) |
| `is_breaking` | boolean | Breaking news flag |
| `category` | string | News category |
| `language` | string | Language code (en/ta/etc) |

---

## Message Processing Flow

### 1. Consumer Receives Message

```
SQS Queue → NewsItConsumer.poll_and_process() → receive_messages()
```

### 2. Message Validation

```python
# Parse JSON body
body = json.loads(message['Body'])

# Validate structure
sqs_message = NewsItSQSMessage(**body)

# Check required fields
if not sqs_message.tenant_id:
    # Skip or reject message
```

### 3. Process Message

```python
# Fetch from NewsIt API
result = await news_service.process_newsit_message(
    message_data=body,
    tenant_id=tenant_id,
    sqs_message_id=message_id
)
```

### 4. Acknowledge or Retry

```python
if result.success:
    # Delete message from queue (acknowledge)
    await sqs_service.delete_message(receipt_handle)
else:
    # Change visibility for retry
    await sqs_service.change_message_visibility(receipt_handle, 300)
```

---

## Testing Workflow

### Step 1: Mock Testing (No Dependencies)

Start with mock testing to validate message structure and flow:

```bash
# Test all scenarios
python test_sqs_mock_trigger.py all
```

This validates:
- ✓ Message structure is correct
- ✓ Consumer can parse messages
- ✓ Error handling works
- ✓ Batch processing works
- ✓ Polling loop works

### Step 2: View Sample Payloads

```bash
# View sample SQS message formats
python test_sqs_message.py --samples-only
```

This shows:
- ✓ Simple SQS message
- ✓ SQS message with metadata
- ✓ Message body schema
- ✓ Required and optional fields

### Step 3: Integration Testing (With Database)

Test with actual processing:

```bash
# Get a valid tenant ID from database
psql -d your_database -c "SELECT id FROM tenants LIMIT 1;"

# Test with tenant ID
python test_sqs_message.py 550e8400-e29b-41d4-a716-446655440000

# Test with specific news ID
python test_sqs_message.py 550e8400-e29b-41d4-a716-446655440000 newsit-12345
```

This validates:
- ✓ NewsIt API fetch works
- ✓ Database insertion works
- ✓ Duplicate detection works
- ✓ Error handling works

---

## Common Test Scenarios

### Scenario 1: Valid Message

**Input**:
```json
{
  "news_id": "newsit-12345",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "newsit"
}
```

**Expected**:
- ✓ Message parsed successfully
- ✓ NewsIt API fetched
- ✓ External news item created
- ✓ Message deleted from queue

### Scenario 2: Missing tenant_id

**Input**:
```json
{
  "news_id": "newsit-12345",
  "source": "newsit"
}
```

**Expected**:
- ⚠️ Warning logged
- ✓ Message deleted (not retried)
- ✗ No processing

### Scenario 3: Malformed JSON

**Input**:
```
"Body": "This is not valid JSON {invalid"
```

**Expected**:
- ❌ Parse error logged
- ✓ Message deleted (prevent infinite retry)
- ✗ No processing

### Scenario 4: NewsIt API Error

**Input**: Valid message but NewsIt API returns 404

**Expected**:
- ❌ API error logged
- ✓ Message visibility changed (retry later)
- ✗ Message not deleted

### Scenario 5: Duplicate Message

**Input**: Message with news_id that already exists in database

**Expected**:
- ✓ Duplicate detected
- ✓ Message deleted (no retry)
- ℹ️ Info logged

---

## Debugging Failed Messages

### Check SQS Queue

```bash
# View queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/newsit-queue \
  --attribute-names All
```

### Check Dead Letter Queue

If messages fail repeatedly, they move to DLQ:

```bash
# Receive from DLQ
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/newsit-dlq \
  --max-number-of-messages 10
```

### Check Consumer Logs

```bash
# View consumer logs
tail -f logs/newsit_consumer.log

# Search for errors
grep "ERROR" logs/newsit_consumer.log

# Search for specific message
grep "message-id-here" logs/newsit_consumer.log
```

### Manual Message Processing

```python
import asyncio
from workers.newsit_consumer import NewsItConsumer

async def test_message():
    consumer = NewsItConsumer()

    # Manually created message
    message = {
        "MessageId": "test-123",
        "ReceiptHandle": "test-receipt",
        "Body": '{"news_id":"newsit-12345","tenant_id":"550e8400-..."}'
    }

    result = await consumer.process_message(message)
    print(f"Result: {result}")

asyncio.run(test_message())
```

---

## Production Deployment

### Environment Variables

Required in `.env`:

```bash
# AWS SQS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/newsit-queue
AWS_SQS_REGION=us-east-1
AWS_SQS_MAX_MESSAGES=10
AWS_SQS_WAIT_TIME=20

# NewsIt API Configuration
NEWSIT_API_KEY=your-newsit-api-key
NEWSIT_API_URL=https://api.newsit.com

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

### Start Consumer

```bash
# Using start script
./start_newsit_consumer.sh start

# Check status
./start_newsit_consumer.sh status

# View logs
./start_newsit_consumer.sh logs -f

# Stop consumer
./start_newsit_consumer.sh stop
```

---

## Monitoring and Alerts

### Metrics to Monitor

1. **Messages Processed**: Count of successfully processed messages
2. **Messages Failed**: Count of failed processing attempts
3. **Processing Time**: Average time to process a message
4. **Queue Depth**: Number of messages waiting in queue
5. **DLQ Depth**: Number of messages in dead letter queue

### CloudWatch Metrics

- `ApproximateNumberOfMessagesVisible`
- `ApproximateNumberOfMessagesNotVisible`
- `NumberOfMessagesSent`
- `NumberOfMessagesReceived`
- `NumberOfMessagesDeleted`

### Alerts to Configure

- ✓ DLQ depth > 0 (messages failing repeatedly)
- ✓ Queue depth > 1000 (processing lag)
- ✓ Consumer process stopped (no heartbeat)
- ✓ Error rate > 10% (high failure rate)

---

## Troubleshooting

### Consumer Not Receiving Messages

**Check**:
1. ✓ AWS credentials valid
2. ✓ Queue URL correct
3. ✓ IAM permissions (ReceiveMessage, DeleteMessage)
4. ✓ Consumer process running
5. ✓ Network connectivity to SQS

**Test**:
```bash
# Send test message to queue
aws sqs send-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/newsit-queue \
  --message-body '{"news_id":"test-123","tenant_id":"550e8400-..."}'
```

### Messages Not Being Deleted

**Check**:
1. ✓ DeleteMessage IAM permission
2. ✓ Receipt handle is valid
3. ✓ Message not past visibility timeout
4. ✓ No exception in processing

**Debug**:
```python
# Add logging in consumer
logger.info(f"Attempting to delete message: {receipt_handle}")
result = await sqs_service.delete_message(receipt_handle)
logger.info(f"Delete result: {result}")
```

### NewsIt API Errors

**Check**:
1. ✓ API key valid
2. ✓ API URL correct
3. ✓ News ID exists in NewsIt
4. ✓ Network connectivity

**Test**:
```bash
# Test NewsIt API directly
curl -H "Authorization: Bearer your-api-key" \
  https://api.newsit.com/news/newsit-12345
```

---

## Best Practices

### 1. Message Idempotency

Always check for duplicates before processing:

```python
# Check if news_id already exists
existing = db.table('external_news_items')\
    .select('id')\
    .eq('external_id', news_id)\
    .eq('tenant_id', tenant_id)\
    .execute()

if existing.data:
    logger.info(f"Duplicate message: {news_id}")
    await sqs_service.delete_message(receipt_handle)
    return True  # Don't retry
```

### 2. Visibility Timeout

Use appropriate visibility timeout for retries:

```python
if processing_failed:
    # 5 minutes delay before retry
    await sqs_service.change_message_visibility(receipt_handle, 300)
```

### 3. Dead Letter Queue

Configure DLQ with max receive count:

```json
{
  "maxReceiveCount": 3,
  "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123456789012:newsit-dlq"
}
```

### 4. Batch Processing

Process multiple messages concurrently:

```python
# Process messages concurrently
tasks = [process_message(msg) for msg in messages]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 5. Graceful Shutdown

Handle SIGTERM for graceful shutdown:

```python
def signal_handler(signum, frame):
    logger.info("Shutting down gracefully...")
    consumer.running = False

signal.signal(signal.SIGTERM, signal_handler)
```

---

## Conclusion

Use the test tools to validate SQS message processing:

1. **Start**: Mock testing (`test_sqs_mock_trigger.py`)
2. **Validate**: Sample payloads (`test_sqs_message.py --samples-only`)
3. **Test**: Integration testing (`test_sqs_message.py <tenant_id>`)
4. **Deploy**: Production consumer (`./start_newsit_consumer.sh start`)
5. **Monitor**: Logs and metrics

For questions or issues, check the logs and use the test tools to isolate the problem.
